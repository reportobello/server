import math
import time
from datetime import UTC, datetime
from urllib.parse import quote

from domin8 import tags as d
from domin8.util import container
from dominate.dom_tag import dom_tag
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from reportobello.api.common import CurrentUser, get_document, json_prettify
from reportobello.api.page.svgs import ARROW_SVG, CODE_SVG
from reportobello.domain.report import Report
from reportobello.infra.db import (
    get_env_vars_for_user,
    get_files_for_template,
    get_recent_report_builds_for_user,
    get_template_for_user,
)

router = APIRouter()


def get_row_loader(name: str, before: datetime) -> dom_tag:
    return d.tr(
        d.td("Loading...", colspan=5, style="text-align: center"),
        hx_trigger="click, intersect once",
        hx_get=f"/template/{name}/builds?before={quote(before.isoformat())}",
        hx_target="this",
        hx_swap="outerHTML",
    )


# TODO: move to domin8
class dialog(d.html_tag):  # noqa: N801
    pass


@router.get("/template/{name}")
async def get(user: CurrentUser, name: str) -> HTMLResponse:
    html = get_document(f"{name} | Reportobello")

    html.add_raw_string(r"""

<style>
table td {
    vertical-align: top;
}

.history-wrapper {
    max-height: 25vh;
    overflow: auto;
}

.history-table-wrapper {
    border: 1px solid gray;
    border-radius: 1em;
    overflow: auto;
    height: calc(100% - 2.5em);
    min-height: 6em;
    padding-right: 1em;
    margin-top: 1em;
}

.expander-inner {
    border: 1px solid gray;
    border-radius: 1em;
    display: flex;
    flex-direction: column;
    gap: 1em;
    padding: 1em;
}

.expander-inner h3 {
    margin: 0;
    margin-top: 1em;
}

.expander-inner table {
    margin: -1em;
    width: fit-content;
}

.expander-inner .delete-button {
    padding: 0 0.5em;
}

table {
    border-spacing: 1em 0.5em;
}

main {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
}

h1 {
    margin: 0;
}

input:not(input[type=file]) {
    color: black;
}

.editor-wrapper {
    display: flex;
    gap: 1em;
    flex: 1;
}

.editor-wrapper details[open]:not(.non-code-expander) {
    height: 100%;
}

.editor-wrapper .inputs {
    display: flex;
    gap: 1em;
    flex-direction: column;
    flex: 1;
    height: 100%;
}

.editor-wrapper textarea {
    width: calc(100% - 2em);
    height: calc(100% - 4em);
    margin: 1em;
    padding: 1em;
    padding-right: 0;
    border: 0;
    border-radius: 1em;
    resize: vertical;
    color: black;
}

.editor-wrapper .iframe-wrapper, .preview-wrapper {
    width: 400px;
    height: 517px;
    border-radius: 6px;
}

.editor-wrapper .iframe-wrapper {
    overflow: hidden;
}

.editor-wrapper .iframe-wrapper .iframe-placeholder-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
}

.editor-wrapper .iframe-wrapper .iframe-placeholder {
    margin: auto;
}

.preview-wrapper {
    position: relative;
    border: 1px solid var(--black);
}

.editor-wrapper iframe {
    /* TODO: make this dynamic */
    width: 400px;
    height: 517px;
    border: 0;
}

th {
    text-align: left;
}

#typst-editor, #json-editor {
    height: calc(100% - 1.5em);
    border-radius: 1em;
    overflow: hidden;
}

.typst-errors {
    position: absolute;
    top: 0;
    z-index: 20;
    overflow: scroll;
    width: calc(100% - 2em);
    height: calc(100% - 2em);
    padding: 1em;
    margin: 0;
    color: var(--red);
    background: #000c;
    border-radius: 4px;
}

dialog[open] {
    display: flex;
}

dialog {
    display: none;
    border: 1px solid var(--black);
    border-radius: 1em;
}

dialog > div {
    display: flex;
    flex-direction: column;
    gap: 1em;
}

dialog h2 {
    margin: 0;
}

dialog::backdrop {
    background: #00000073
}

dialog code {
  border-radius: 1em;
  display: block;
  overflow: hidden;
}

button.dialog-close {
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--black);
  background: transparent;
  padding: 0 0.5em;
  margin-bottom: auto;
}

#file-upload-expander div.form {
  display: flex;
  flex-direction: column;
  gap: 1em;
}

#file-upload-expander table td {
    vertical-align: middle;
}

#upload-error {
    color: var(--red);
}

@media (max-width: 1000px) {
    body, main {
        height: 100%;
    }

    .editor-wrapper {
        flex-direction: column;
    }

    .editor-wrapper .inputs {
        height: fit-content;
        flex: 0;
    }

    #typst-editor, #json-editor {
        min-height: 50vh;
    }

    .hide-on-mobile {
        display: none;
    }

    .delete-button {
        margin-left: auto;
    }
}
</style>

<script src="/www/node_modules/monaco-editor/min/vs/loader.js"></script>

<script>
require.config({ paths: { vs: '/www/node_modules/monaco-editor/min/vs' } });

let previous = undefined;

const ignoreKeys = new Set(["Insert", "Home", "End", "PageUp", "PageDown", "Escape", "ScrollLock", "Pause", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]);

function debounceJsonPreview() {
    let timer;

    return (e) => {
        if (
            e.altKey
            || e.ctrlKey
            || e.metaKey
            || ignoreKeys.has(e.code)
        ) {
            return;
        }

        clearTimeout(timer);

        const isAutomatic = document.getElementById("automatic-reload").checked;

        if (!isAutomatic) {
            document.getElementById("manual-reload").disabled = false;
            return;
        }

        const errors = document.querySelector(".typst-errors");
        errors.style.display = "none";

        try {
            const raw = JSON.stringify(JSON.parse(window.jsonEditor.getValue())) + window.typstEditor.getValue();

            if (raw === previous) return;

            document.querySelector("iframe").style.opacity = 0.5;
            document.querySelector(".iframe-placeholder").innerHTML = "";

            timer = setTimeout(onPreviewEdit, 250);
        } catch {}
    };
}

function toggleAutomaticReload() {
    const automaticBuildButton = document.getElementById("automatic-reload");
    const reloadButton = document.getElementById("manual-reload");

    if (automaticBuildButton.checked) {
        reloadButton.style.display = "none";
    } else {
        reloadButton.style.display = "inline";
    }
}

// TODO: dedupe
function debounceTypstPreview() {
    let timer;

    return (e) => {
        if (
            e.altKey
            || e.ctrlKey
            || e.metaKey
            || ignoreKeys.has(e.code)
        ) {
            return;
        }

        const publishButton = document.getElementById("publish-version");
        publishButton.disabled = false;
        publishButton.title = null;

        clearTimeout(timer);

        const isAutomatic = document.getElementById("automatic-reload").checked;

        if (!isAutomatic) {
            document.getElementById("manual-reload").disabled = false;
            return;
        }

        const errors = document.querySelector(".typst-errors");
        errors.style.display = "none";

        try {
            const raw = JSON.stringify(JSON.parse(window.jsonEditor.getValue())) + window.typstEditor.getValue();

            if (raw === previous) return;

            document.querySelector("iframe").style.opacity = 0.5;
            document.querySelector(".iframe-placeholder").innerHTML = "";

            timer = setTimeout(onPreviewEdit, 250);
        } catch {}
    };
}

require(['vs/editor/editor.main'], function () {
    window.typstEditor = monaco.editor.create(document.getElementById('typst-editor'), {
        value: "",
        language: "plaintext",
        minimap: {enabled: false},
        theme: "vs-dark",
        tabSize: 2,
        fontSize: 10,
        padding: {top: 8},
    });

    window.jsonEditor = monaco.editor.create(document.getElementById('json-editor'), {
        value: "{}",
        language: "json",
        minimap: {enabled: false},
        theme: "vs-dark",
        tabSize: 2,
        fontSize: 10,
        padding: {top: 8},
    });

    jsonEditor.onKeyUp(debounceJsonPreview());
    typstEditor.onKeyUp(debounceTypstPreview());
});

function closeExamples() {
    document.querySelector("dialog").close();
}

function json2Csharp(x) {
  if (Array.isArray(x)) {
    if (x.length === 0) return "Array.Empty<object>()";

    return `new[] {${x.map(json2Csharp).join(", ")}}`;
  }
  if (typeof(x) === "object") {
    if (Object.keys(x).length === 0) return "new {}";

    const inner = Object.entries(x)
      .filter(y => y[1] !== null)
      .map(y => `${y[0]}=${json2Csharp(y[1])}`)
      .join(", ");

    return `new { ${inner} }`;
  }
  if (typeof(x) === "string") {
    return JSON.stringify(x);
  }
  return x.toString();
}

function json2python(x) {
  if (Array.isArray(x)) {
    return `[${x.map(json2python).join(", ")}]`;
  }
  if (typeof(x) === "object") {
    const inner = Object.entries(x)
      .filter(y => y[1] !== null)
      .map(y => `${JSON.stringify(y[0])}: ${json2python(y[1])}`)
      .join(", ");

    return `{${inner}}`;
  }
  if (typeof(x) === "boolean") {
    return x ? "True" : "False";
  }
  if (typeof(x) === "string") {
    return JSON.stringify(x);
  }
  return x.toString();
}

function showExamples(e) {
    if (e.type === "keyup" && ![" ", "Enter"].includes(e.key)) {
        return;
    }

    document.querySelector("dialog").showModal();

require(['vs/editor/editor.main'], function () {
  const templateNameRaw = location.pathname.trimRight("/").split("/").at(-1);
  const templateName = JSON.stringify(templateNameRaw);

  const host = `${location.protocol}//${location.host}`;
  const defaultHost = "https://reportobello.com";

  const valueRaw = JSON.parse(window.jsonEditor.getValue());
  const value = JSON.stringify(valueRaw);

  const jsCode = `
import { Reportobello, download } from "reportobello";

const api = new Reportobello({apiKey: "rpbl_API_KEY_HERE"${host !== defaultHost ? `, host: "${host}"` : ""}});

const data = ${value};
api.runReport(${templateName}, data).then(download);
`;

  const csharpCode = `
using Reportobello;

var api = new ReportobelloApi("rpbl_API_KEY_HERE"${host !== defaultHost ? `, "${host}"` : ""});

var data = ${json2Csharp(valueRaw)};
var url = await api.RunReport(${templateName}, report);
`;

  const pythonCode = `
from reportobello import ReportobelloApi

api = ReportobelloApi("rpbl_API_KEY_HERE"${host !== defaultHost ? `, host="${host}"` : ""})

data = ${json2python(valueRaw)}
pdf = await api.build_template(${templateName}, data)

await pdf.save_to("output.pdf")
`;

  const curlCode = `
curl "${host}/api/v1/template/${templateNameRaw}/build" \\
    -H "Authorization: Bearer rpbl_API_KEY_HERE" \\
    -H "Content-Type: application/json" \\
    -d '{"content_type": "application/json", "data": ${value}}'
`;

  const commonOptions = {
    minimap: {
      enabled: false,
      showMarkSectionHeaders: false,
      showRegionSectionHeaders: false,
    },
    automaticLayout: true,
    theme: "vs-dark",
    fontSize: 12,
    lineNumbers: "off",
    scrollbar: {
      horizontal: "hidden",
      vertical: "hidden",
    },
    selectOnLineNumbers: false,
    codeLens: false,
    contextmenu: false,
    readOnly: true,
    domReadOnly: true,
    padding: {
      top: 18,
      bottom: 18,
    },
    selectOnLineNumbers: false,
    selectionHighlight: false,
  };

  monaco.editor.create(document.querySelector("#js-example"), {
    ...commonOptions,
    value: jsCode.trim(),
    language: "javascript",
    tabSize: 2
  });

  monaco.editor.create(document.querySelector("#csharp-example"), {
    ...commonOptions,
    value: csharpCode.trim(),
    language: "csharp",
    tabSize: 4
  });

  monaco.editor.create(document.querySelector("#python-example"), {
    ...commonOptions,
    value: pythonCode.trim(),
    language: "python",
    tabSize: 4
  });

  monaco.editor.create(document.querySelector("#curl-example"), {
    ...commonOptions,
    value: curlCode.trim(),
    language: "shell",
    tabSize: 4
  });
});

}
</script>

<script type="module">

import { Reportobello, openInIframe } from "/www/node_modules/reportobello/dist/index.js";

const api = new Reportobello({apiKey: getCookie("api_key"), host: `${location.protocol}//${location.host}`});

window.onPreviewEdit = () => {
    const templateName = location.pathname.trimRight("/").split("/").at(-1);

    try {
        const data = JSON.parse(window.jsonEditor.getValue());
        const template = window.typstEditor.getValue();

        previous = JSON.stringify(data) + template;

        api.runReportAsBlob(templateName, data, {rawTemplate: template})
            .then(blob => {
                const url = URL.createObjectURL(blob);
                const iframe = document.querySelector("iframe");

                openInIframe(url, "iframe");

                iframe.style.opacity = 1;
            })
            .catch(e => {
                const errors = document.querySelector(".typst-errors");
                errors.style.display = "block";
                errors.innerText = e;
            });
    } catch {}
};

window.manuallyRebuild = () => {
    document.getElementById("manual-reload").disabled = true;

    onPreviewEdit();

    const errors = document.querySelector(".typst-errors");
    errors.style.display = "none";
}

window.resizeEditors = () => {
    const typstEditorElement = document.getElementById("typst-editor");
    const jsonEditorElement = document.getElementById("json-editor");

    // use set timeout to force elements to resize on next tick
    setTimeout(() => {
        typstEditorElement.style.height = "0";
        typstEditorElement.style.width = "0";
        jsonEditorElement.style.height = "0";
        jsonEditorElement.style.width = "0";
        window.typstEditor.layout();
        window.jsonEditor.layout();

        setTimeout(() => {
            typstEditorElement.style.height = "calc(100% - 1.5em)";
            jsonEditorElement.style.height = "calc(100% - 1.5em)";
            typstEditorElement.style.width = "100%";
            jsonEditorElement.style.width = "100%";
            window.typstEditor.layout();
            window.jsonEditor.layout();
        }, 0);

    }, 0);

};

window.formSubmitted = false;

window.publishNewTemplateVersion = () => {
    const templateName = location.pathname.trimRight("/").split("/").at(-1);

    api.createOrUpdateTemplate(templateName, typstEditor.getValue()).then(() => {
        const data = JSON.parse(window.jsonEditor.getValue());

        api.runReport(templateName, data).then(() => {
            window.formSubmitted = true;
            location.reload(true);
        });
    });
};

window.customFileUpload = (e) => {
    e.preventDefault();

    document.getElementById("file-upload").click();
};

window.updateForm = (element) => {
    const fileLabel = document.querySelector("#file-upload-expander label.filename");
    const file = document.getElementById("file-upload");
    const submit = document.querySelector("#file-upload-expander [type=submit]");

    if (file.files.length === 0) {
        submit.disabled = true;
        fileLabel.innerText = "No file(s) selected";
    } else {
        const filename = [...file.files].map(x => x.name).join(", ");

        fileLabel.innerText = filename;

        submit.disabled = false;
    }
};

window.uploadDataFiles = () => {
    const templateName = location.pathname.trimRight("/").split("/").at(-1);

    const files = document.getElementById("file-upload");

    api.uploadDataFiles(templateName, files.files)
        .then(() => {
            htmx.ajax(
                "GET",
                `/template/${templateName}/files`,
                {target: "#file-upload-expander table", swap: "outerHTML"},
            ).then(() => {
                files.value = "";
                updateForm();

                document.getElementById("upload-error").style.display = "none";
            });
        })
        .catch(e => {
            const err = document.getElementById("upload-error");

            err.innerText = e.message;
            err.style.display = "flex";
        });
};
</script>

<script>
window.addEventListener("load", () => {
    const data = document.getElementById("json-editor").dataset.value;
    const template = document.getElementById("typst-editor").dataset.value;

    jsonEditor.setValue(data);
    typstEditor.setValue(template);

    previous = JSON.stringify(JSON.parse(data)) + template;

    if (window.matchMedia("(max-width: 1000px)").matches) {
        document.querySelector(".history-wrapper").open = false;
    }

    /*
    // TODO: this is too overzealous with HTMX. Need to figure out a better solution
    // TODO: detect if PDF fails to load, then re-run preview
    window.addEventListener("beforeunload", e => {
        if (window.formSubmitted) {
            return;
        }

        const msg = "You have unpublished template changes. Are you sure you want to leave this page?";

        (e || window.event).returnValue = msg;
        return msg;
    });
    */

    // Force disable this button to fix firefox bug
    document.querySelector("#file-upload-expander [type=submit]").disabled = true;
});

let debounceResizer = null;

window.addEventListener("resize", () => {
    if (debounceResizer != null) clearTimeout(debounceResizer);

    debounceResizer = setTimeout(resizeEditors, 150);
});

const dialog = document.querySelector("dialog");
dialog.addEventListener("click", () => dialog.close());

const dialogContent = document.querySelector("dialog > div");
dialogContent.addEventListener("click", e => e.stopPropagation());
</script>
""")

    template = get_template_for_user(user.id, name)

    if template:
        reports = get_recent_report_builds_for_user(user.id, name, before=datetime.now(tz=UTC))

        env_vars = [
            d.tr(d.td(k), d.td(v))
            for k, v in get_env_vars_for_user(user.id).items()
        ]

        if not env_vars:
            env_vars.append(
                d.tr(d.td("No Environment Variables", colspan=2))
            )

        code_examples = dialog(
            d.div(
                d.h1(
                    d.span(
                        "Quick Export",
                        d.button(
                            "x",
                            onclick="closeExamples()",
                            style="margin-left: auto",
                            autofocus=True,
                            _class="dialog-close",
                        ),
                        style="display: flex",
                    ),
                ),
                d.div(
                    d.h2("C#"),
                    d.code(id="csharp-example", style="height: 11em"),
                ),
                d.div(
                    d.h2("Python"),
                    d.code(id="python-example", style="height: 14em"),
                ),
                d.div(
                    d.h2("TypeScript/JavaScript"),
                    d.code(id="js-example", style="height: 11em"),
                ),
                d.div(
                    d.h2("cURL"),
                    d.code(id="curl-example", style="height: 8em"),
                ),
                style="width: 100%",
            ),
            style="position: absolute; width: 50vw",
        )

        reload_buttons = d.div(
            d.button(
                "Reload",
                id="manual-reload",
                disabled=True,
                style="display: none",
                onclick="manuallyRebuild()",
            ),
            d.input_(
                id="automatic-reload",
                type="checkbox",
                checked=True,
                onclick="toggleAutomaticReload()",
                # https://bugzilla.mozilla.org/show_bug.cgi?id=654072#c68
                name=time.time(),
            ),
            d.label(
                "Automatic Reload",
                _for="automatic-reload",
                style="font-size: 0.75em; font-weight: normal; margin: auto 0",
            ),
        )

        html.add(
            d.main(
                code_examples,
                d.h1(
                    d.div(
                        ARROW_SVG,
                        hx_get="/",
                        hx_swap="outerHTML",
                        hx_target="body",
                        hx_push_url="true",
                        style="height: 24px; margin: auto 0; cursor: pointer",
                    ),
                    d.span(template.name),
                    d.span(
                        f" (revision {template.version})",
                        style="font-size: 0.5em; color: #919191; margin: auto 0 0.25em 0",
                        _class="hide-on-mobile",
                    ),
                    d.button(
                        "Delete",
                        hx_delete=f"/api/v1/template/{name}",
                        hx_confirm="Are you sure you want to delete this template and all reports built from this template? This cannot be undone.",
                        _class="red-outline delete-button",
                    ),
                    d.div(
                        CODE_SVG,
                        onclick="showExamples(event)",
                        onKeyUp="showExamples(event)",
                        style="height: 24px; margin: auto 0 auto auto; cursor: pointer",
                        title="Quick Export",
                        _class="hide-on-mobile",
                        tabindex="0",
                    ),
                    style="margin-bottom: 0.5em; display: flex; gap: 0.5em",
                ),
                d.details(
                    d.summary("Build History", onclick="resizeEditors()"),
                    d.div(
                        d.table(
                            d.tr(
                                *[d.th(x) for x in ("Status", "Version", "Finished At", "Data", "PDF")],
                                _class="table-header",
                            ),
                            get_row_loader(name, before=datetime.now(tz=UTC))
                        ),
                        _class="history-table-wrapper",
                    ),
                    _class="history-wrapper",
                    open=True,
                ),
                d.h2(
                    d.span("Preview Editor"),
                    d.div(
                        d.button(
                            "Publish Template",
                            id="publish-version",
                            _class="green",
                            onclick="publishNewTemplateVersion()",
                            disabled=True,
                            title="Modify the template to publish a new version",
                            style="margin-right: auto;",
                            # https://bugzilla.mozilla.org/show_bug.cgi?id=654072#c68
                            name=time.time(),
                        ),
                    ),
                    reload_buttons,
                    style="margin-bottom: 0.5em; display: flex; gap: 0.5em; flex-wrap: wrap",
                ),
                d.div(
                    d.div(
                        d.details(
                            d.summary(
                                "Template",
                                style="height: 1.5em",
                                onclick="resizeEditors()",
                            ),
                            d.div(
                                id="typst-editor",
                                data_value=template.template,
                                style="height: calc(100% - 1.5em)",
                            ),
                            open=True,
                        ),
                        d.details(
                            d.summary(
                                "Data",
                                style="height: 1.5em",
                                onclick="resizeEditors()",
                            ),
                            d.div(
                                id="json-editor",
                                data_value=json_prettify(reports[0].data or "{}") if reports else "",
                                style="height: calc(100% - 1.5em)",
                            ),
                            open=True,
                            onclick="resizeEditors",
                        ),
                        d.details(
                            d.summary(
                                "Files",
                                style="height: 1.5em",
                                onclick="resizeEditors()",
                            ),
                            d.div(
                                d.div(hx_get=f"/template/{name}/files", hx_trigger="load", hx_swap="outerHTML"),
                                d.h3("Upload File(s)"),
                                d.div(
                                    d.div(
                                        d.label(
                                            d.span(
                                                d.button("Upload", id="file-upload-button", onclick="customFileUpload(event)"),
                                                d.label(
                                                    "No file selected",
                                                    style="flex: 1; margin: auto; margin-left: 1em; text-align: left",
                                                    _class="filename",
                                                    _for="file-upload-button",
                                                ),
                                                style="display: flex",
                                            ),
                                            _for="file-upload",
                                            style="display: flex; width: fit-content",
                                        ),
                                        d.input_(
                                            id="file-upload",
                                            name="file",
                                            type="file",
                                            multiple=True,
                                            onchange="updateForm(this)",
                                            style="display: none",
                                        ),
                                    ),
                                    d.button(
                                        "Submit",
                                        type="submit",
                                        disabled=True,
                                        style="width: min-content",
                                        _class="green",
                                        onclick="uploadDataFiles()",
                                    ),
                                    d.span("", id="upload-error", style="display: none"),
                                    _class="form",
                                ),
                                _class="expander-inner",
                            ),
                            _class="non-code-expander",
                            id="file-upload-expander",
                        ),
                        d.details(
                            d.summary(
                                "Environment Variables",
                                style="height: 1.5em",
                                onclick="resizeEditors()",
                            ),
                            d.div(
                                d.table(
                                    d.tr(d.th(x) for x in ("Key", "Value")),
                                    *env_vars,
                                ),
                                _class="expander-inner",
                            ),
                            _class="non-code-expander",
                        ),
                        _class="inputs",
                    ),
                    d.div(
                        d.pre(_class="typst-errors", style="display: none"),
                        d.div(
                            d.div(
                                d.span("Download Expired", _class="iframe-placeholder"),
                                _class="iframe-placeholder-wrapper",
                            ),
                            d.iframe(
                                src=(
                                    f"/api/v1/files/{reports[0].filename}#toolbar=0&navpanes=0&view=FitH"
                                    if reports and reports[0].filename
                                    else "about:blank"
                                ),
                                style="position: relative; z-index: 10",
                            ),
                            _class="iframe-wrapper",
                        ),
                        _class="preview-wrapper",
                    ),
                    _class="editor-wrapper",
                ),
            ),
        )

    else:
        html.add(d.h1("Template ", name, " was not found"))

    return HTMLResponse(html.render())


def build_row(report: Report) -> dom_tag:
    status = d.span("OK", _class="green chip") if report.was_successful else d.span("FAIL", _class="red chip")

    if not report.was_successful:
        action = d.details(
            d.summary("Show Errors"),
            d.pre(report.error_message, style="color: red") or ""
        )
    elif report.filename:
        action = d.a(
            "Download",
            target="_blank",
            rel="noopener noreferrer",
            href=f"/api/v1/files/{report.filename}?download=1&downloadAs={quote(report.template_name)}.pdf",
        )
    else:
        action = d.span("Download expired")

    return d.tr(
        d.td(status, _class="min"),
        d.td(report.actual_version, title=f"Requested version {report.requested_version}", _class="min"),
        d.td(data_utc_localize=report.finished_at.isoformat(), _class="min", style="white-space: nowrap"),
        d.td(
            d.details(
                d.summary(f"Show {report.data_type.title()}", style="white-space: nowrap", onclick="resizeEditors()"),
                # TODO: don't assume this is json
                d.pre(json_prettify(report.data or "{}")),
            ),
        ),
        d.td(action, style="white-space: nowrap"),
    )


@router.get("/template/{name}/builds")
async def get_builds(user: CurrentUser, name: str, before: datetime | None = None) -> HTMLResponse:
    limit = 20

    recent = get_recent_report_builds_for_user(user.id, name, before=before, limit=limit)

    if not recent:
        if before is None:
            return HTMLResponse(d.tr(d.td("No recent builds", colspan=5)).render())

        return HTMLResponse("")

    done = container(
        *[build_row(r) for r in recent]
    )

    if len(recent) >= limit:
        done.add(get_row_loader(name, before=recent[-1].started_at))

    return HTMLResponse(done.render())


@router.get("/template/{name}/files")
async def get_files(user: CurrentUser, name: str) -> HTMLResponse:
    def make_delete_button(filename: str):
        button = d.button(
            "Delete",
            hx_confirm="Are you sure you want to delete this file?",
            hx_delete=f"/api/v1/template/{name}/file/{filename}",
            hx_swap="delete",
            hx_target="closest tr",
            _class="red-outline delete-button",
        )

        button["hx-on::afterSettle"] = "resizeEditors()"

        return button

    files = [
        d.tr(
            d.td(
                d.a(
                    file.filename,
                    href=f"/api/v1/template/{name}/file/{file.filename}",
                    target="_blank",
                    rel="noopener noreferrer",
                ),
            ),
            d.td(
                prettify_byte_size(file.size),
                title=f"{file.size:,} bytes",
                style="text-align: right",
            ),
            d.td(make_delete_button(file.filename)),
        )
        for file in get_files_for_template(user.id, name)
    ]

    headers = ("Filename", "Size", "Delete")

    if not files:
        files.append(
            d.tr(d.td("No Files", colspan=len(headers), style="text-align: center"))
        )

    html = d.table(
        d.tr(d.th(x) for x in headers),
        *files
    )

    return HTMLResponse(html.render())


# https://stackoverflow.com/a/14822210
def prettify_byte_size(size: int) -> str:
    if size == 0:
        return "0B"

    sizes = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")

    i = math.floor(math.log(size, 1000))
    p = math.pow(1000, i)
    s = round(size / p, 1)

    return f"{s}{sizes[i]}"
