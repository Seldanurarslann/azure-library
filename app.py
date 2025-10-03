from flask import Flask, render_template, request, jsonify, session
import os
import secrets
import pathlib
import json
import base64
import re
from typing import Any, Dict, Tuple, List

import requests
import xml.etree.ElementTree as ET

# ---------------------- SECRET KEY (env var > file) ----------------------
def load_or_create_secret(path: str = ".flask_secret_key") -> str:
    """
    Prefer environment variable FLASK_SECRET_KEY.
    If missing, load from a local file (created once). Keeps sessions stable across restarts.
    """
    env_key = os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key.strip()

    p = pathlib.Path(path)
    if p.exists():
        return p.read_text().strip()

    key = secrets.token_hex(32)  # 32 bytes → 64 hex chars
    p.write_text(key)
    try:
        os.chmod(p, 0o600)  # best-effort harden
    except Exception:
        pass
    return key


app = Flask(__name__)
app.config["SECRET_KEY"] = load_or_create_secret()

# ---------------------- Helpers ----------------------
SECRET_PATTERNS = re.compile(
    r"(secret|token|password|passwd|apikey|api_key|client_secret|connectionstring|conn_str|key)$",
    re.IGNORECASE,
)

def is_secret_key(key_path: str) -> bool:
    last = key_path.split(".")[-1]
    last = last.split("_")[-1]
    return bool(SECRET_PATTERNS.search(last))

def flatten_json(obj: Any, parent_key: str = "") -> Dict[str, str]:
    out: Dict[str, str] = {}

    def _walk(x: Any, pk: str):
        if isinstance(x, dict):
            for k, v in x.items():
                new_key = f"{pk}.{k}" if pk else str(k)
                _walk(v, new_key)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                new_key = f"{pk}.{i}" if pk else str(i)
                _walk(v, new_key)
        else:
            val = "" if x is None else str(x)
            out[pk] = val

    _walk(obj, parent_key)
    return out

def parse_web_config(xml_bytes: bytes, section_prefix: bool = True) -> Dict[str, str]:
    out: Dict[str, str] = {}
    root = ET.fromstring(xml_bytes)

    app_settings = root.find("appSettings")
    if app_settings is not None:
        for add in app_settings.findall("add"):
            k = add.attrib.get("key")
            v = add.attrib.get("value")
            if k and v is not None:
                key = f"appSettings.{k}" if section_prefix else k
                out[key] = v

    conns = root.find("connectionStrings")
    if conns is not None:
        for add in conns.findall("add"):
            name = add.attrib.get("name")
            cs = add.attrib.get("connectionString")
            if name and cs is not None:
                key = f"connectionStrings.{name}" if section_prefix else name
                out[key] = cs

    return out

def build_auth_header(pat_token: str) -> Dict[str, str]:
    pat_bytes = f":{pat_token}".encode("utf-8")
    pat_base64 = base64.b64encode(pat_bytes).decode("utf-8")
    return {"Authorization": f"Basic {pat_base64}"}

def get_project_id(organization: str, project: str, pat_token: str) -> Tuple[bool, str]:
    url = f"https://dev.azure.com/{organization}/_apis/projects/{project}?api-version=7.1-preview.4"
    headers = {"Content-Type": "application/json", **build_auth_header(pat_token)}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return True, r.json().get("id", "")
    else:
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        return False, f"{r.status_code}: {msg}"

def create_variable_group(
    organization: str,
    project: str,
    project_id: str,
    vg_name: str,
    description: str,
    variables_table: List[Dict],
    pat_token: str,
):
    url = f"https://dev.azure.com/{organization}/_apis/distributedtask/variablegroups?api-version=7.1"
    headers = {"Content-Type": "application/json", **build_auth_header(pat_token)}

    variables: Dict[str, Dict[str, object]] = {}
    for row in variables_table:
        key = str(row.get("key", "")).strip()
        if not key:
            continue
        variables[key] = {
            "value": str(row.get("value", "")),
            **({"isSecret": True} if bool(row.get("isSecret", False)) else {}),
        }

    payload = {
        "type": "Vsts",
        "name": vg_name,
        "description": description or "Created via Flask UI",
        "variables": variables,
        "variableGroupProjectReferences": [
            {
                "projectReference": {"id": project_id, "name": project},
                "name": vg_name,
                "description": description or "Created via Flask UI",
            }
        ],
    }

    r = requests.post(url, headers=headers, json=payload)
    return r, payload

# Initialize session variables
def init_session():
    if "variables" not in session:
        session["variables"] = []
    if "form_data" not in session:
        session["form_data"] = {
            "organization": "",
            "project": "",
            "pat_token": "",
            "variable_group_name": "",
            "vg_description": "JSON / web.config'den otomatik oluşturuldu",
        }

@app.route("/")
def index():
    init_session()
    return render_template(
        "index.html",
        variables=session.get("variables", []),
        form_data=session.get("form_data", {}),
    )

@app.route("/load_data", methods=["POST"])
def load_data():
    init_session()

    try:
        data = request.get_json()
        input_type = data.get("type")  # 'json' or 'xml'
        content = data.get("content", "")

        current_vars = {var["key"]: var for var in session.get("variables", [])}

        if input_type == "json":
            json_data = json.loads(content)
            flat = flatten_json(json_data)
            for k, v in flat.items():
                current_vars[k] = {"key": k, "value": v, "isSecret": False}
            session["variables"] = list(current_vars.values())
            return jsonify(
                {
                    "success": True,
                    "message": f"JSON: {len(flat)} anahtar okundu.",
                    "variables": session["variables"],
                }
            )

        elif input_type == "xml":
            xml_map = parse_web_config(content.encode("utf-8"), section_prefix=False)
            for k, v in xml_map.items():
                current_vars[k] = {"key": k, "value": v, "isSecret": False}
            session["variables"] = list(current_vars.values())
            return jsonify(
                {
                    "success": True,
                    "message": f"XML: {len(xml_map)} anahtar okundu.",
                    "variables": session["variables"],
                }
            )

        else:
            return jsonify({"success": False, "message": "Geçersiz tür (json/xml)."})
    except json.JSONDecodeError as e:
        return jsonify({"success": False, "message": f"JSON okunamadı: {str(e)}"})
    except ET.ParseError as e:
        return jsonify({"success": False, "message": f"XML parse hatası: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata: {str(e)}"})

@app.route("/update_variables", methods=["POST"])
def update_variables():
    init_session()

    try:
        data = request.get_json()
        variables = data.get("variables", [])
        session["variables"] = variables
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/create_variable_group", methods=["POST"])
def create_vg():
    init_session()

    try:
        data = request.get_json()

        # Form verilerini kaydet
        form_data = {
            "organization": data.get("organization", ""),
            "project": data.get("project", ""),
            "pat_token": data.get("pat_token", ""),
            "variable_group_name": data.get("variable_group_name", ""),
            "vg_description": data.get("vg_description", ""),
        }
        session["form_data"] = form_data

        variables = data.get("variables", [])

        # Validasyon
        missing = []
        for label, val in [
            ("Organization", form_data["organization"]),
            ("Project", form_data["project"]),
            ("PAT Token", form_data["pat_token"]),
            ("Variable Group Name", form_data["variable_group_name"]),
        ]:
            if not str(val).strip():
                missing.append(label)

        if missing:
            return jsonify(
                {"success": False, "message": f"Eksik alanlar: {', '.join(missing)}"}
            )

        if not variables:
            return jsonify({"success": False, "message": "En az bir değişken ekleyin."})

        # Proje ID'sini al
        ok, pid_or_err = get_project_id(
            form_data["organization"], form_data["project"], form_data["pat_token"]
        )
        if not ok:
            return jsonify(
                {
                    "success": False,
                    "message": f"Proje bilgileri alınamadı: {pid_or_err}",
                }
            )

        # Variable Group oluştur
        resp, _ = create_variable_group(
            organization=form_data["organization"],
            project=form_data["project"],
            project_id=pid_or_err,
            vg_name=form_data["variable_group_name"],
            description=form_data["vg_description"],
            variables_table=variables,
            pat_token=form_data["pat_token"],
        )

        if resp.status_code in (200, 201):
            resp_data = resp.json()
            success_msg = (
                "Variable Group başarıyla oluşturuldu! 🎉 "
                f"ID: {resp_data.get('id')} | Ad: {resp_data.get('name')} | "
                f"Değişken sayısı: {len(resp_data.get('variables', {}))}"
            )

            # Başarılı oluşturma sonrası temizle
            session["variables"] = []

            return jsonify({"success": True, "message": success_msg})
        else:
            try:
                err = resp.json()
            except Exception:
                err = {"raw": resp.text}
            return jsonify(
                {
                    "success": False,
                    "message": f"Hata: {resp.status_code}",
                    "error_detail": err,
                }
            )

    except Exception as e:
        return jsonify({"success": False, "message": f"Beklenmeyen hata: {str(e)}"})

if __name__ == "__main__":
    # Üretimde FLASK_SECRET_KEY ortam değişkenini set etmeyi unutmayın:
    # export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    app.run(debug=True)
