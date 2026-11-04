"""Minimal Meshy API client: submit image-to-3D / multi-image-to-3D jobs and download results.

The API key is read from the MESHY_API_KEY environment variable (never stored in the repo).
  python meshy_client.py submit NAME img1.jpg [img2.jpg ...] [--res 4k]
  python meshy_client.py wait NAME          (polls, then downloads the GLB/STL into work/meshy/NAME/)
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request

API = "https://api.meshy.ai/openapi/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "work", "meshy")


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + os.environ["MESHY_API_KEY"],
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def data_uri(path):
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def submit(name, images, res):
    common = {"ai_model": "latest", "should_texture": False, "target_formats": ["glb", "stl"],
              "multi_view_thumbnails": True}
    if len(images) == 1:
        kind = "image-to-3d"
        body = dict(common, image_url=data_uri(images[0]), geometry_resolution=res)
    else:
        kind = "multi-image-to-3d"
        body = dict(common, image_urls=[data_uri(p) for p in images], geometry_resolution="2k" if res == "4k" else res)
    task = call("POST", f"/{kind}", body)["result"]
    os.makedirs(os.path.join(OUT, name), exist_ok=True)
    json.dump({"kind": kind, "task": task, "images": images}, open(os.path.join(OUT, name, "task.json"), "w"))
    print(name, kind, task)


def wait(name):
    meta = json.load(open(os.path.join(OUT, name, "task.json")))
    while True:
        t = call("GET", f"/{meta['kind']}/{meta['task']}")
        if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
            break
        time.sleep(15)
    json.dump(t, open(os.path.join(OUT, name, "result.json"), "w"), indent=1)
    print(name, t["status"], "credits", t.get("consumed_credits"), t.get("task_error"))
    if t["status"] != "SUCCEEDED":
        sys.exit(1)
    for key, url in list(t.get("model_urls", {}).items()) + [("thumb", t.get("thumbnail_url"))] + \
            [("thumb_" + k, v) for k, v in (t.get("thumbnail_urls") or {}).items()]:
        if url:
            ext = {"glb": ".glb", "stl": ".stl"}.get(key, ".png")
            urllib.request.urlretrieve(url, os.path.join(OUT, name, key + ext))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "wait"])
    ap.add_argument("name")
    ap.add_argument("images", nargs="*")
    ap.add_argument("--res", default="4k")
    a = ap.parse_args()
    submit(a.name, a.images, a.res) if a.cmd == "submit" else wait(a.name)
