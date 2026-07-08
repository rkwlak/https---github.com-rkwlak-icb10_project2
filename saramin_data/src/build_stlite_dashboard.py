"""dashboard.py를 stlite(Pyodide 기반 Streamlit 브라우저 런타임)로 감싼
단일 self-contained HTML 파일을 생성한다. 서버 없이 더블클릭만으로 열람 가능.

- DB(saramin.db)는 base64로 인코딩해 HTML 안에 그대로 내장한다.
- gap_analysis.json도 텍스트로 내장한다.
- 원본 dashboard.py의 경로 상수(DB_PATH, GAP_REPORT_PATH)는 실제 프로젝트 폴더 구조
  기준 상대경로라 Pyodide 가상 파일시스템에서는 의미가 없으므로, 마운트할 고정 경로
  (/mount/data/...)로 치환한다.
"""

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # icb10_project2/
DASHBOARD_PY = Path(__file__).parent / "dashboard.py"
DB_PATH = ROOT / "saramin_data" / "data" / "saramin.db"
GAP_JSON_PATH = ROOT / "linkareer" / "report" / "gap_analysis.json"
OUT_HTML = Path(__file__).parent.parent / "report" / "dashboard_stlite.html"

MOUNT_DB_PATH = "/mount/data/saramin.db"
MOUNT_GAP_PATH = "/mount/data/gap_analysis.json"


def build_app_source() -> str:
    src = DASHBOARD_PY.read_text(encoding="utf-8")

    # 실제 파일 경로 기준 상수 -> Pyodide 가상 파일시스템 고정 경로로 치환
    src = re.sub(
        r'DB_PATH = Path\(__file__\)\.parent\.parent / "data" / "saramin\.db"',
        f'DB_PATH = "{MOUNT_DB_PATH}"',
        src,
    )
    src = re.sub(
        r'GAP_REPORT_PATH = Path\(__file__\)\.parent\.parent\.parent / "linkareer" / "report" / "gap_analysis\.json"',
        f'GAP_REPORT_PATH = Path("{MOUNT_GAP_PATH}")',
        src,
    )
    return src


def main() -> None:
    app_source = build_app_source()
    db_b64 = base64.b64encode(DB_PATH.read_bytes()).decode("ascii")
    gap_json_text = GAP_JSON_PATH.read_text(encoding="utf-8")

    # json.dumps로 이스케이프를 전부 맡겨 백틱/${}/따옴표 등 JS 문법 충돌을 원천 차단한다.
    app_source_js = json.dumps(app_source)
    db_b64_js = json.dumps(db_b64)
    gap_json_js = json.dumps(gap_json_text)
    mount_db_path_js = json.dumps(MOUNT_DB_PATH)
    mount_gap_path_js = json.dumps(MOUNT_GAP_PATH)

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>사람인 데이터 직무 분석 대시보드</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@0.85.1/build/stlite.css" />
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; }}
  #loading {{
    position: fixed; inset: 0; display: flex; flex-direction: column; align-items: center;
    justify-content: center; background: #0e1117; color: #e2e8f0; font-family: system-ui, sans-serif;
    gap: 12px; z-index: 9999;
  }}
  #loading .spinner {{
    width: 36px; height: 36px; border: 4px solid #2d3748; border-top-color: #4a9eff;
    border-radius: 50%; animation: spin 0.9s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>
  <div id="loading">
    <div class="spinner"></div>
    <div>대시보드를 불러오는 중입니다 (최초 로딩 10~30초 소요)...</div>
  </div>
  <div id="root"></div>

  <script type="module">
    import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@0.85.1/build/stlite.js";

    const appSource = {app_source_js};
    const dbBase64 = {db_b64_js};
    const gapJsonText = {gap_json_js};
    const dbPath = {mount_db_path_js};
    const gapPath = {mount_gap_path_js};

    function base64ToUint8Array(base64) {{
      const binaryStr = atob(base64);
      const bytes = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {{
        bytes[i] = binaryStr.charCodeAt(i);
      }}
      return bytes;
    }}

    mount(
      {{
        requirements: ["pandas", "plotly", "sqlite3"],
        entrypoint: "streamlit_app.py",
        files: {{
          "streamlit_app.py": appSource,
          [dbPath]: base64ToUint8Array(dbBase64),
          [gapPath]: gapJsonText,
        }},
      }},
      document.getElementById("root"),
    );

    // mount()가 thenable을 반환하지 않는 stlite 버전도 있어, 실제 앱 DOM이
    // 렌더링되는 시점을 MutationObserver로 감지해 로딩 오버레이를 제거한다.
    const rootEl = document.getElementById("root");
    const removeLoading = () => {{
      const loading = document.getElementById("loading");
      if (loading) loading.remove();
    }};
    const observer = new MutationObserver(() => {{
      if (rootEl.querySelector('[data-testid="stApp"], [data-testid="stAppViewContainer"]')) {{
        removeLoading();
        observer.disconnect();
      }}
    }});
    observer.observe(rootEl, {{ childList: true, subtree: true }});
    // 혹시 감지에 실패해도 무한정 로딩 화면에 갇히지 않도록 안전장치를 둔다.
    setTimeout(removeLoading, 120000);
  </script>
</body>
</html>
"""

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"saved: {OUT_HTML} ({OUT_HTML.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
