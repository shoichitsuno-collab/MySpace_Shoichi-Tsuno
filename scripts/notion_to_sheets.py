import os
import json
from notion_client import Client
import gspread
from google.oauth2.service_account import Credentials

# --- 設定 ---
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = "2065fb52a4aa8192afaad9de6c633c4d"
SPREADSHEET_ID = "1hXY98qPVNWG_yTup9bj6hiLCVY3FYjO4hhFr_tEnep8"
SHEET_NAME = "CCテスト"  # 書き込み先のシート名

# --- Notion接続 ---
notion = Client(auth=NOTION_API_KEY)

# --- Google Sheets接続 ---
credentials_json = os.environ["GOOGLE_SHEETS_CREDENTIALS"]
credentials_dict = json.loads(credentials_json)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# --- Notionからデータ取得 ---
def get_notion_data():
    results = []
    has_more = True
    next_cursor = None

    while has_more:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            start_cursor=next_cursor
        )
        results.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response.get("next_cursor")

    return results

# --- プロパティの値を文字列に変換 ---
def parse_property(prop):
    prop_type = prop["type"]

    if prop_type == "title":
        return "".join([t["plain_text"] for t in prop["title"]])
    elif prop_type == "rich_text":
        return "".join([t["plain_text"] for t in prop["rich_text"]])
    elif prop_type == "number":
        return prop["number"] if prop["number"] is not None else ""
    elif prop_type == "select":
        return prop["select"]["name"] if prop["select"] else ""
    elif prop_type == "multi_select":
        return ", ".join([s["name"] for s in prop["multi_select"]])
    elif prop_type == "date":
        if prop["date"]:
            start = prop["date"]["start"]
            end = prop["date"].get("end", "")
            return f"{start} - {end}" if end else start
        return ""
    elif prop_type == "checkbox":
        return "Yes" if prop["checkbox"] else "No"
    elif prop_type == "url":
        return prop["url"] or ""
    elif prop_type == "email":
        return prop["email"] or ""
    elif prop_type == "phone_number":
        return prop["phone_number"] or ""
    elif prop_type == "people":
        return ", ".join([p.get("name", "") for p in prop["people"]])
    elif prop_type == "status":
        return prop["status"]["name"] if prop["status"] else ""
    elif prop_type == "formula":
        formula = prop["formula"]
        return str(formula.get(formula["type"], ""))
    else:
        return ""

# --- メイン処理 ---
def main():
    print("Notionからデータ取得中...")
    pages = get_notion_data()

    if not pages:
        print("データが見つかりませんでした")
        return

    # ヘッダー行の取得（最初のページのプロパティ名を使用）
    headers = list(pages[0]["properties"].keys())

    # データ行の作成
    rows = []
    for page in pages:
        row = []
        for header in headers:
            prop = page["properties"].get(header, {})
            row.append(parse_property(prop))
        rows.append(row)

    # スプレッドシートをクリアして書き込み
    print("スプレッドシートに書き込み中...")
    sheet.clear()
    sheet.append_row(headers)
    sheet.append_rows(rows)

    print(f"完了: {len(rows)}件のデータを書き込みました")

if __name__ == "__main__":
    main()
