import os
import json
import base64
import hashlib
import struct
import time
import random
from flask import Flask, request, make_response
from Crypto.Cipher import AES

app = Flask(__name__)

TOKEN = os.environ.get("WECOM_BOT_TOKEN", "")
ENCODING_AES_KEY = os.environ.get("WECOM_BOT_AESKEY", "")
DEFAULT_RECEIVE_ID = os.environ.get("WECOM_BOT_RECEIVE_ID", "")  # 可选：没拿到 body.tousername 时兜底

BLOCK_SIZE = 32


def sha1_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    arr = [token, timestamp, nonce, encrypt]
    arr.sort()
    raw = "".join(arr).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def pkcs7_pad(data: bytes) -> bytes:
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError("Invalid PKCS7 padding")
    return data[:-pad_len]


def get_aes_key(aes_key_43: str) -> bytes:
    # 43位 EncodingAESKey，base64 decode时需要补 '='
    key = base64.b64decode(aes_key_43 + "=")
    if len(key) != 32:
        raise ValueError("Invalid AES key length (expect 32 bytes)")
    return key


def decrypt(encrypt_b64: str, receive_id: str) -> str:
    key = get_aes_key(ENCODING_AES_KEY)
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)

    plain_padded = cipher.decrypt(base64.b64decode(encrypt_b64))
    plain = pkcs7_unpad(plain_padded)

    # plain = random(16) + msg_len(4) + msg + receive_id
    msg_len = struct.unpack("!I", plain[16:20])[0]
    msg = plain[20:20 + msg_len]
    rid = plain[20 + msg_len:].decode("utf-8")

    if receive_id and rid != receive_id:
        raise ValueError(f"receive_id mismatch: got={rid}, expect={receive_id}")

    return msg.decode("utf-8")


def encrypt(reply_plaintext: str, receive_id: str, timestamp: str, nonce: str) -> str:
    key = get_aes_key(ENCODING_AES_KEY)
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)

    rand16 = bytes(random.getrandbits(8) for _ in range(16))
    msg_bytes = reply_plaintext.encode("utf-8")
    msg_len = struct.pack("!I", len(msg_bytes))

    raw = rand16 + msg_len + msg_bytes + receive_id.encode("utf-8")
    raw_padded = pkcs7_pad(raw)

    encrypt_b64 = base64.b64encode(cipher.encrypt(raw_padded)).decode("utf-8")
    sig = sha1_signature(TOKEN, timestamp, nonce, encrypt_b64)

    # 注意：不少语言 SDK 的 EncryptMsg 返回的是 XML 包装体（Encrypt/MsgSignature/TimeStamp/Nonce）
    # 你贴的 Java 示例也是直接 return EncryptMsg(...) 的结果（通常就是这个 XML）。:contentReference[oaicite:2]{index=2}
    resp_xml = f"""<xml>
<Encrypt><![CDATA[{encrypt_b64}]]></Encrypt>
<MsgSignature><![CDATA[{sig}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
    return resp_xml


@app.route("/wecom/aibot/callback", methods=["POST"])
def callback():
    # 企微会带：msg_signature / timestamp / nonce
    msg_signature = request.args.get("msg_signature", "")
    timestamp = request.args.get("timestamp", str(int(time.time())))
    nonce = request.args.get("nonce", "nonce")

    # 回调 body：JSON，至少包含 encrypt；有的实现还会带 tousername / agentid 等字段 :contentReference[oaicite:3]{index=3}
    body = request.get_json(force=True, silent=False)
    encrypt_b64 = body.get("encrypt", "")
    receive_id = body.get("tousername") or DEFAULT_RECEIVE_ID

    if not (TOKEN and ENCODING_AES_KEY):
        return make_response("server not configured: missing token/aeskey", 500)
    if not encrypt_b64:
        return make_response("missing encrypt field", 400)
    if not receive_id:
        return make_response("missing receive_id (tousername or env WECOM_BOT_RECEIVE_ID)", 400)

    # 1) 验签
    calc_sig = sha1_signature(TOKEN, timestamp, nonce, encrypt_b64)
    if calc_sig != msg_signature:
        return make_response("bad signature", 401)

    # 2) 解密得到明文 JSON（你贴的官方示例就是这种结构：msgid/aibotid/response_url/msgtype/text.content...）
    try:
        plain = decrypt(encrypt_b64, receive_id=receive_id)
        event = json.loads(plain)
    except Exception as e:
        return make_response(f"decrypt/parse failed: {e}", 400)

    # 3) 只做 text demo
    msgtype = event.get("msgtype")
    reply_obj = None
    if msgtype == "text":
        content = (event.get("text") or {}).get("content", "")
        reply_obj = {
            "msgtype": "text",
            "text": {"content": f"收到：{content}\n（Python demo 自动回复）"}
        }
    else:
        reply_obj = {
            "msgtype": "text",
            "text": {"content": f"收到 {msgtype} 类型消息（demo暂只处理 text）"}
        }

    # 4) 加密被动回复并返回
    reply_plain = json.dumps(reply_obj, ensure_ascii=False)
    resp_xml = encrypt(reply_plain, receive_id=receive_id, timestamp=timestamp, nonce=nonce)
    return make_response(resp_xml, 200, {"Content-Type": "application/xml"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)