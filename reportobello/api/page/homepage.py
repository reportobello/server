from domin8 import tags as d
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from reportobello.api.common import get_document, security
from reportobello.config import IS_LIVE_SITE
from reportobello.infra.db import get_all_templates_for_user

router = APIRouter()


@router.get("/")
async def get(request: Request):  # noqa: ANN201
    try:
        user = await security(request)

    except HTTPException:
        if IS_LIVE_SITE:
            return FileResponse("www/index.html", headers={"Vary": "Cookie"})

        else:
            return RedirectResponse("/login")

    html = get_document("Reportobello")

    html.add_raw_string(
r"""
<style>
button[type=submit] {
    width: max-content;
    margin: auto;
    padding: 0.5em 1em;
    color: var(--black);
    border: none;
    border-radius: 0.5em;
    background: var(--green);
    cursor: pointer;
}

h1, h2, h3 {
    margin: 0;
}

main {
    display: flex;
    flex-direction: column;
    gap: 2em;
}

main > div {
    display: flex;
    flex-direction: column;
    gap: 0.25em;
}

ol {
    display: flex;
    flex-direction: column;
    gap: 1em;
    padding-left: 1em;
    list-style: none;
}

fieldset {
    border: none;
    display: flex;
    flex: ;
    flex-direction: column;
    gap: 2em;
    margin: 1em 0 2em 0;
    padding: 0;
}

#buttons {
    position: fixed;
    top: 1em;
    right: 1em;
    display: flex;
    gap: 1em;
    flex-direction: row;
}

#doc-links {
    display: flex;
    flex-wrap: wrap;
    gap: 2em;
}

@media (max-width: 1000px) {
    #buttons {
        position: relative;
        top: 0;
        right: 0;
        margin-left: auto;
    }

    #doc-links {
        gap: 1em
    }
}
</style>

<script type="module">
import { Reportobello, openInIframe } from "/www/node_modules/reportobello/dist/index.js";

window.customFileUpload = (e) => {
    e.preventDefault();

    document.getElementById("pdf-upload").click();
}

window.submitForm = (element) => {
    if (event.key === "Enter") {
        createNewTemplate();
    }
};

window.updatePdfForm = (element) => {
    const name = document.querySelector("#new-template-form [name=template_name]");
    const file = document.querySelector("#new-template-form [type=file]");
    const fileLabel = document.querySelector("#new-template-form label.filename");
    const submit = document.querySelector("#new-template-form [type=submit]");

    const blankSelected = document.getElementById("blank-template-type").checked;

    const fileSelected = document.getElementById("existing-template-type").checked;
    let fileUploaded = false;

    if (blankSelected || element.id === "blank-template-type") {
        // ignore
    }
    else if (file.files.length !== 0) {
        fileLabel.innerText = file.files[0].name;

        document.getElementById("existing-template-type").checked = true;

        fileUploaded = true;
    }

    submit.disabled = !(name.value && (fileUploaded || blankSelected));

    if (fileSelected && !fileUploaded) {
        submit.title = "Please upload a file";
    } else if (!blankSelected && !fileSelected) {
        submit.title = "Please pick a template type";
    } else if (!name.value) {
        submit.title = "Please pick a template name";
    } else {
        submit.title = "";
    }
}

function getCookie(name) {
    return document.cookie.split(";").map(x => x.split("=")).filter(x => x[0].trim() === name)?.[0]?.[1];
}

const api = new Reportobello({apiKey: getCookie("api_key"), host: `${location.protocol}//${location.host}`});

window.createNewTemplate = () => {
    document.getElementById("create-template").disabled = true;

    const template_name = document.querySelector("#new-template-form [name=template_name]").value;
    const file = document.querySelector("#new-template-form [type=file]");

    if (file.files.length > 0) {
        const data = new FormData();

        data.append("template_name", template_name);
        data.append("pdf", file.files[0]);

        // TODO: use reportobello API library
        fetch("/api/v1/convert/pdf", { method: "POST", body: data }).then(e => {
            location.href = `/template/${template_name}`;
        });
    } else {
        const name = document.querySelector("#new-template-form [name=template_name]").value;

        const blankTemplate = `
// Example of how to set page/margin size
#set page("us-letter", margin: (x: 50pt, y: 50pt))

// When rendering, template data is stored in "data.json", so use this to load it.
#let data = json("data.json")

// Set default font family/size
#set text(font: "JetBrains Mono", size: 20pt)

= Example Header

== Example Subheader

Supplied data:

#data

// If statement example
#if data.conditional [
    data.conditional is true
] else [
    data.conditional is false
]

// Table example
#table(
    columns: (1fr, 1fr),
    align: (left, right),
    table.header([Description], [Count]),
    ..data.table.map(x => (x.item, x.count)).flatten()
)

#text(fill: rgb(data.color.code))[#data.color.text]
`;

        // TODO: add a way to seed template with test data?
        api.createOrUpdateTemplate(name, blankTemplate.trim()).then(_ => {
            const exampleData = {
                conditional: true,
                table: [
                    {item: "Nut", count: "10"},
                    {item: "Bolt", count: "10"},
                ],
                color: {
                    code: "#abc123",
                    text: "Dynamically colored text",
                },
            };

            api.runReport(name, exampleData).then(() => {
                location.href = `/template/${name}`;
            });
        });
    }
}
</script>
"""
    )

    rows = get_all_templates_for_user(user.id)

    templates = [
        d.li(d.a(row.name, href=f"/template/{row.name}", hx_boost="false"))
        # TODO: sort by most recently used
        for row in sorted(rows, key=lambda x: x.name)
    ]

    if not templates:
        templates.append(d.li("No templates yet"))

    buttons = d.div(
        d.a(
            d.button("Settings", _class="outline"),
            href="/settings",
            tabindex="-1",
        ),
        d.button(
            "Logout",
            hx_confirm="Are you sure you want to log out?",
            hx_get="/logout",
            _class="outline",
        ),
        id="buttons",
    )

    documentation_links = d.div(
        d.h2("Documentation"),
        d.span(
            d.a("Home", target="_blank", rel="noopener noreferrer", href="/docs"),
            d.a("Swagger Docs", target="_blank", rel="noopener noreferrer", href="/swagger"),
            d.a("C#", target="_blank", rel="noopener noreferrer", href="/docs/libraries/csharp.html"),
            d.a("JS/TS", target="_blank", rel="noopener noreferrer", href="/docs/libraries/typescript.html"),
            d.a("Python", target="_blank", rel="noopener noreferrer", href="/docs/libraries/python.html"),
            d.a("Typst Templates", target="_blank", rel="noopener noreferrer", href="https://typst.app/docs/reference"),
            id="doc-links",
        ),
    )

    create_templates = d.div(
        d.h2("Create New Template"),
        d.div(
            d.fieldset(
                d.div(
                    d.input_(
                        id="blank-template-type",
                        type="radio",
                        name="type",
                        value="blank",
                        onclick="updatePdfForm(this)",
                    ),
                    d.label("Blank template", _for="blank-template-type"),
                ),
                d.div(
                    d.div(
                        d.input_(
                            id="existing-template-type",
                            type="radio",
                            name="type",
                            value="import",
                            onclick="updatePdfForm(this)",
                        ),
                        d.label("Create from existing file (PDF, DOCX, or Markdown)", _for="existing-template-type"),
                    ),
                    d.div(
                        d.label(
                            d.span(
                                d.button("Upload", id="pdf-upload-button", onclick="customFileUpload(event)", _class="green"),
                                d.label(
                                    "No file selected",
                                    style="flex: 1; margin: auto; margin-left: 1em; text-align: left",
                                    _class="filename",
                                    _for="pdf-upload-button",
                                ),
                                style="display: flex; padding-left: 2.5em",
                            ),
                            _for="pdf-upload",
                            style="display: flex; width: fit-content",
                        ),
                        d.input_(
                            required=True,
                            id="pdf-upload",
                            name="pdf",
                            type="file",
                            accept=".pdf,.md,.docx,.doc",
                            onchange="updatePdfForm(this)",
                            style="display: none",
                        ),
                    ),
                    style="width: 100%; display: flex; flex-direction: column; gap: 1em",
                ),
            ),
            d.div(
                d.input_(
                    required=True,
                    placeholder="Template name",
                    name="template_name",
                    autocomplete=False,
                    oninput="updatePdfForm(this)",
                    onkeydown="submitForm(event)",
                ),
                d.button(
                    "Create",
                    id="create-template",
                    type="submit",
                    onclick="createNewTemplate()",
                    disabled=True,
                    title="Please pick out a template type",
                ),
            ),
            id="new-template-form",
        ),
    )

    main = d.main(
        buttons,
        d.h1("Reportobello"),
        documentation_links,
        d.div(
            d.h2("Recent Templates"),
            d.ol(templates),
        ),
        create_templates,
    )

    html.add(main)

    return HTMLResponse(html.render(), headers={"Vary": "Cookie"})
