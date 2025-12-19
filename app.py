from flask import Flask, request, jsonify
import requests, time, random, string

app = Flask(__name__)

MAILTM_API = "https://api.mail.tm"
TOKENS = {}  # email -> token

def rand_str(n=10):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def create_account():
    domains = requests.get(f"{MAILTM_API}/domains").json()["hydra:member"]
    domain = domains[0]["domain"]

    email = f"{rand_str()}@{domain}"
    password = rand_str(12)

    # create account
    r = requests.post(
        f"{MAILTM_API}/accounts",
        json={"address": email, "password": password}
    )
    r.raise_for_status()

    # get token
    token = requests.post(
        f"{MAILTM_API}/token",
        json={"address": email, "password": password}
    ).json()["token"]

    return email, password, token

def wait_verify_link(token, timeout=35):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()

    while time.time() - start < timeout:
        r = requests.get(f"{MAILTM_API}/messages", headers=headers)
        if r.status_code == 200:
            for msg in r.json().get("hydra:member", []):
                body = (msg.get("text") or "") + " ".join(msg.get("html") or [])
                for part in body.split():
                    if part.startswith("http"):
                        return part
        time.sleep(2)
    return None

# ================= DROP-IN API =================

@app.route("/api/v2/create-email", methods=["POST"])
def create_email():
    # รับ payload api-key เฉย ๆ เพื่อให้โค้ดเดิมคุณผ่าน
    _ = request.json.get("api-key") if request.is_json else None

    try:
        email, password, token = create_account()
        TOKENS[email] = token

        return jsonify({
            "success": True,
            "data": {
                "email": email,
                "password": password
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/v2/<path:email>/get_link", methods=["GET"])
def get_link(email):
    # รับ password ผ่าน json เพื่อให้โค้ดเดิมคุณผ่าน
    _ = request.json.get("password") if request.is_json else None

    token = TOKENS.get(email)
    if not token:
        return jsonify({"success": False})

    link = wait_verify_link(token)
    if link:
        return jsonify({"success": True, "verify_link": link})

    return jsonify({"success": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
