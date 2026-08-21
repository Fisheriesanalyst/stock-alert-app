import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import time
import json
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import japanize_matplotlib
import streamlit.components.v1 as components

# --- デフォルトの銘柄データ（7銘柄） ---
default_data = [
    {"区分": "個別株", "銘柄名": "極洋", "コード": "1301.T"},
    {"区分": "個別株", "銘柄名": "日本たばこ", "コード": "2914.T"},
    {"区分": "個別株", "銘柄名": "イオン", "コード": "8267.T"},
    {"区分": "個別株", "銘柄名": "キンバリークラーク", "コード": "KMB"},
    {"区分": "個別株", "銘柄名": "コカコーラ", "コード": "KO"},
    {"区分": "個別株", "銘柄名": "スペースX", "コード": "SPCX"},
    {"区分": "投資信託", "銘柄名": "インベスコ 世界厳選株式＜H無＞", "コード": "18312991"}
]

# --- 画面設定 ---
st.set_page_config(page_title="株価・投資信託 チェックボード", page_icon="📈", layout="centered")

# --- セッションステートの初期化 ---
if 'import_count' not in st.session_state:
    st.session_state['import_count'] = 0

if 'portfolio' not in st.session_state:
    st.session_state['portfolio'] = pd.DataFrame(default_data)

# カスタムCSS
st.markdown("""
<style>
/* 右上のヘッダーメニューを非表示 */
[data-testid="stHeader"] {
    display: none !important;
}

/* 右下のStreamlitアイコン（バッジ）やフッターを非表示 */
.viewerBadge_container, 
.viewerBadge_link, 
#viewerBadge,
[data-testid="stAppDeployButton"],
[data-testid="stToolbar"],
[data-testid="ManageAppBadge"],
a[href*="streamlit.io/cloud"],
a[href*="share.streamlit.io"],
footer {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

@media (max-width: 768px) {
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
        margin-bottom: 10px !important;
    }
}

/* 3つのボタンの高さを60pxに統一 */
div.stButton > button, 
div.stDownloadButton > button {
    width: 100% !important;
    height: 60px !important;
    border-radius: 6px !important;
    font-weight: bold !important;
    font-size: 15px !important;
    border: none !important;
}

div.stButton > button { background-color: #1f77b4 !important; color: white !important; }
div.stButton > button:hover { background-color: #155a8a !important; color: white !important; }

div.stDownloadButton > button { background-color: #2ca02c !important; color: white !important; }
div.stDownloadButton > button:hover { background-color: #217c21 !important; color: white !important; }

/* ファイルアップローダーのデザイン */
div[data-testid="stFileUploader"] { width: 100% !important; }
div[data-testid="stFileUploader"] > label { display: none !important; }
div[data-testid="stFileUploader"] section {
    background-color: #fff3e0 !important;
    border: 2px dashed #ff7f0e !important;
    border-radius: 6px !important;
    min-height: 60px !important;
    padding: 5px !important;
}
div[data-testid="stFileUploader"] small { display: none !important; }
div[data-testid="stFileUploader"] section button {
    background-color: #ff7f0e !important;
    color: white !important;
    border: none !important;
    font-weight: bold !important;
    border-radius: 4px !important;
}
div[data-testid="stFileUploader"] section button:hover { background-color: #d6680b !important; }
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown("<h3 style='text-align: center;'>📊 株価・投資信託 チェックボード</h3>", unsafe_allow_html=True)

# --- 画像と説明文 ---
try:
    st.image("25rule_minimized.jpg", use_container_width=True)
except Exception:
    st.warning("画像ファイル「25rule_minimized.jpg」が読み込めません。GitHubへのアップロードを確認してください。")

st.info("""
**💡 株式投資における「25%ルール」**\n
「直近の最高値から株価が25%以上下落した時点で売却（損切り・利益確定）を検討する」というシンプルな原則です。値上がり局面での早すぎる利益確定を防ぎつつ、急落時には逃げ遅れを回避し、大切な資産を守る効果が期待できます。\n
本アプリでは、登録した保有銘柄の過去1年間の最高値を基準に現在の下落率を自動計算し、3段階でアラートを表示します。日々の投資判断のサポートとしてご活用ください。
""")

# 色分けの説明文を追加
st.markdown("""
<div style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px; padding: 0 10px;">
    個別株式のアラートはグラフの色でも表示します
</div>
<div style="font-size: 1.0em; margin-bottom: 20px; padding: 0 10px; font-weight: bold;">
    <span style="color: #1f77b4;">15％未満：青色のグラフ</span><br>
    <span style="color: #ffb300;">15％～25％：黄色のグラフ</span><br>
    <span style="color: #d62728;">25％以上：赤色のグラフ</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- マニュアルダウンロード ---
try:
    with open("運用マニュアル20260803.pdf", "rb") as pdf_file:
        st.download_button(
            label="📄 運用マニュアルをダウンロード",
            data=pdf_file,
            file_name="運用マニュアル20260803.pdf",
            mime="application/pdf",
            type="primary"
        )
except FileNotFoundError:
    st.warning("運用マニュアル（運用マニュアル20260803.pdf）が読み込めません。GitHubへのアップロードを確認してください。")

# --- ブラウザのローカルストレージ（各ユーザー固有）を利用した保存・読み込み処理 ---
storage_key = "stock_portfolio_local_v5"

# ローカルストレージからデータを取得・同期するためのJavaScriptコンポーネント
storage_code = f"""
<script>
const STORAGE_KEY = "{storage_key}";

// 1. ページ読み込み時に保存データがあればStreamlit側へ通知する仕組み
window.addEventListener("DOMContentLoaded", () => {{
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && !window.parent.document.getElementById("loaded_data_flag")) {{
        // 初回ロード時にデータを渡す隠し要素を作成
        const flag = document.createElement("div");
        flag.id = "loaded_data_flag";
        window.parent.document.body.appendChild(flag);
    }});
}});

// 2. 外部から保存命令を受けたときの関数
function saveToLocal(dataJson) {{
    localStorage.setItem(STORAGE_KEY, dataJson);
    console.log("LocalStorage Saved!");
}}
</script>
"""
components.html(storage_code, height=0)

# --- 1. 銘柄の管理機能 ---
st.markdown("#### 1. 銘柄の登録・管理")
st.markdown("以下の表を直接クリックして銘柄を追加・編集・削除できます。変更した内容は、**「🌐 ブラウザに記憶させる」**ボタンを押すことで、**あなたがお使いのブラウザ内（ローカル）にのみ**安全に保存されます。")

editor_key = f"portfolio_editor_{st.session_state['import_count']}"

edited_df = st.data_editor(
    st.session_state['portfolio'],
    key=editor_key,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "区分": st.column_config.SelectboxColumn("区分", options=["個別株", "投資信託"], required=True),
        "銘柄名": st.column_config.TextColumn("銘柄名", required=True),
        "コード": st.column_config.TextColumn("コード", required=True)
    }
)
st.session_state['portfolio'] = edited_df
df = st.session_state['portfolio']

st.markdown("<br>", unsafe_allow_html=True) 

col1, col2, col3 = st.columns(3)

# 1. ブラウザ保存ボタン（青）
with col1:
    if st.button("🌐 ブラウザに記憶させる", use_container_width=True):
        try:
            json_str = df.to_json(orient='records', force_ascii=False)
            # ブラウザのLocalStorageに保存するJavaScriptを実行
            js_code = f"""
            <script>
            localStorage.setItem("{storage_key}", {json.dumps(json_str)});
            </script>
            """
            components.html(js_code, height=0)
            st.success("✅ このブラウザ専用に銘柄リストを記憶させました！（他のユーザーには影響しません）")
        except Exception as e:
            st.error(f"保存に失敗しました。詳細: {e}")

# 2. エクスポートボタン（緑）
with col2:
    export_json = df.to_json(orient='records', force_ascii=False)
    st.download_button(
        label="💾 銘柄リストをエクスポート",
        data=export_json,
        file_name="portfolio_data.json",
        mime="application/json",
        use_container_width=True
    )

# 3. ファイルからのインポート（PC用）
with col3:
    uploaded_file = st.file_uploader("📂 インポート(ファイル)", label_visibility="collapsed")
    if uploaded_file is not None:
        file_id = uploaded_file.file_id
        if st.session_state.get('last_uploaded_id') != file_id:
            try:
                bytes_data = uploaded_file.getvalue()
                json_str = None
                for enc in ['utf-8-sig', 'utf-8', 'cp932', 'shift_jis']:
                    try:
                        json_str = bytes_data.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if json_str:
                    imported_data = json.loads(json_str)
                    st.session_state['portfolio'] = pd.DataFrame(imported_data)
                    st.session_state['import_count'] += 1
                    st.session_state['last_uploaded_id'] = file_id
                    
                    # ブラウザのLocalStorageも同時に更新
                    new_json_str = st.session_state['portfolio'].to_json(orient='records', force_ascii=False)
                    js_code = f"""
                    <script>
                    localStorage.setItem("{storage_key}", {json.dumps(new_json_str)});
                    </script>
                    """
                    components.html(js_code, height=0)
                    
                    st.success("✅ ファイルからデータを復元しました！")
                    time.sleep(0.3)
                    st.rerun() 
            except Exception as e:
                st.error(f"ファイルインポートに失敗: {e}")

# --- Android等でファイル選択が機能しない場合の「テキスト貼り付けルート」 ---
with st.expander("📲 Androidでファイルが選べない場合のインポート（テキスト貼り付け）"):
    st.info("PCで保存したJSONファイルをメモ帳等で開き、中の文字をすべてコピーして下の枠に貼り付けてください。")
    json_text_input = st.text_area("JSONテキストをここに貼り付け", height=100, label_visibility="collapsed")
    
    if st.button("📝 テキストデータからインポートを強制実行", type="primary"):
        if json_text_input.strip():
            try:
                imported_data_from_text = json.loads(json_text_input.strip())
                if isinstance(imported_data_from_text, list):
                    st.session_state['portfolio'] = pd.DataFrame(imported_data_from_text)
                    st.session_state['import_count'] += 1
                    
                    new_json_str = st.session_state['portfolio'].to_json(orient='records', force_ascii=False)
                    js_code = f"""
                    <script>
                    localStorage.setItem("{storage_key}", {json.dumps(new_json_str)});
                    </script>
                    """
                    components.html(js_code, height=0)
                    
                    st.success("✅ テキストからデータを完全に復元しました！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("JSONデータの形式が間違っています。")
            except Exception as e:
                st.error(f"テキストの読み込みに失敗しました。コピー漏れがないか確認してください。（エラー詳細: {e}）")
        else:
            st.warning("枠内にJSONテキストが貼り付けられていません。")

tickers = dict(zip(df[df['区分'] == '個別株']['銘柄名'], df[df['区分'] == '個別株']['コード']))
funds = dict(zip(df[df['区分'] == '投資信託']['銘柄名'], df[df['区分'] == '投資信託']['コード']))

st.markdown("---")
st.markdown("#### 2. 株価・基準価額の確認")

if st.button("🔄 最新データを取得してチェックする", type="primary"):
    
    # ========================================
    # 個別株チェック
    # ========================================
    st.markdown("##### 個別株式")
    results = []
    alerts = []
    
    if len(tickers) > 0:
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_stocks = len(tickers)
        
        for i, (name, ticker) in enumerate(tickers.items()):
            status_text.text(f"個別株取得中... {name} ({i+1}/{total_stocks})")
            progress_bar.progress((i + 1) / total_stocks)
            
            try:
                stock = yf.Ticker(str(ticker).strip())
                hist = stock.history(period="1y")
                
                if hist.empty:
                    st.warning(f"[{name}] データの取得に失敗しました。")
                    continue
                    
                current_price = hist['Close'].iloc[-1]
                high_price = hist['High'].max()
                drop_ratio = (high_price - current_price) / high_price
                
                judgment = "⚠️ アラート (25%以上下落)" if drop_ratio >= 0.25 else "✅ 基準内"
                line_color = '#d62728' if drop_ratio >= 0.25 else ('#ffb300' if drop_ratio > 0.15 else '#1f77b4')

                results.append({
                    "銘柄名": name,
                    "コード": ticker,
                    "最新株価": round(current_price, 2),
                    "1年内高値": round(high_price, 2),
                    "下落率(%)": round(drop_ratio * 100, 2),
                    "判定": judgment
                })
                
                if drop_ratio >= 0.25:
                    alerts.append(f"⚠️ **{name}** ({ticker}) が直近高値から **{round(drop_ratio*100, 2)}%** 下落！ (高値: {round(high_price, 2)} -> 現在値: {round(current_price, 2)})")
                
                six_months_ago = hist.index.max() - pd.DateOffset(months=6)
                hist_6m = hist[hist.index >= six_months_ago]
                hist_6m.index = hist_6m.index.strftime('%m-%d')

                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(hist_6m.index, hist_6m['Close'], color=line_color, linewidth=2, marker='o', markersize=4)
                ax.set_title(f"「{name}」株価推移（過去6ヶ月）", fontsize=14, fontweight='bold', pad=15)
                
                info_text = f"1年以内高値: {round(high_price, 2)}\n現在値: {round(current_price, 2)}\n下落率: {round(drop_ratio * 100, 2)}%"
                ax.annotate(info_text, xy=(0.02, 0.95), xycoords='axes fraction', fontsize=10, color='#333', ha='left', va='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.9))

                last_idx = len(hist_6m) - 1
                last_y = hist_6m['Close'].iloc[-1]
                ax.text(last_idx, last_y, f"  {round(last_y, 2)}", fontsize=11, fontweight='bold', va='center', color=line_color)

                ax.grid(True, linestyle=':', color='gray', alpha=0.6)
                ax.set_xlim(-1, last_idx + (last_idx * 0.1))
                ax.set_xticks(range(0, len(hist_6m.index), 10))
                ax.set_xticklabels(hist_6m.index[::10], rotation=45) 
                
                plt.tight_layout()
                
                with st.expander(f"{name} のグラフを見る", expanded=True):
                    st.pyplot(fig)
                plt.close()
                    
            except Exception as e:
                st.error(f"[{name}] エラーが発生しました: {e}")

        status_text.text("個別株の取得完了！")
        
        st.dataframe(
            pd.DataFrame(results),
            use_container_width=True,
            column_config={
                "判定": st.column_config.TextColumn("判定", width="medium")
            }
        )

        if alerts:
            st.error("#### 📉 25%下落アラート\n" + "\n".join(alerts))
        else:
            st.success("現在、直近高値から25%以上下落している個別銘柄はありません。")
    else:
        st.info("個別株が登録されていません。")

    st.markdown("---")

    # ========================================
    # 投資信託チェック
    # ========================================
    st.markdown("#### 投資信託")
    
    st.markdown("<p style='color: red; font-size: 0.95em; font-weight: bold;'>注）投資信託については、複数銘柄のパフォーマンス比較を目的としておりグラフの表示期間は過去１年間です。またグラフ色は銘柄識別を優先したので直近最高値からの下落幅を示していません。</p>", unsafe_allow_html=True)
    
    if len(funds) > 0:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        try:
            if os.path.exists("/usr/bin/chromedriver"):
                service = Service("/usr/bin/chromedriver")
                options.binary_location = "/usr/bin/chromium"
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            st.error(f"ブラウザドライバの起動に失敗しました。システム環境を確認してください。詳細: {e}")
            st.stop()
        
        status_text_fund = st.empty()
        progress_bar_fund = st.progress(0)
        total_funds = len(funds)
        
        limit_date_1y = datetime.now() - timedelta(days=365)
        
        fund_data_dict = {}

        for i, (name, code) in enumerate(funds.items()):
            status_text_fund.text(f"投資信託取得中... {name} ({i+1}/{total_funds})")
            progress_bar_fund.progress((i + 1) / total_funds)
            
            url = f"https://finance.yahoo.co.jp/quote/{str(code).strip()}/history"
            driver.get(url)
            time.sleep(5)
            
            all_html = []
            for page in range(15):
                all_html.append(driver.page_source)
                try:
                    next_btn = driver.find_element(By.XPATH, "//*[contains(text(), '次へ')]")
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)
                except:
                    break

            full_df = pd.DataFrame()
            for html in all_html:
                try:
                    dfs = pd.read_html(io.StringIO(html))
                    for temp_df in dfs:
                        cols = [str(c) for c in temp_df.columns]
                        if len(cols) >= 2 and any('日付' in c for c in cols):
                            date_col = [c for c in cols if '日付' in c][0]
                            price_col = [c for c in cols if c != date_col][0]
                            
                            df_piece = temp_df[[date_col, price_col]].copy()
                            df_piece.columns = ['Date', 'Price']
                            full_df = pd.concat([full_df, df_piece])
                            break
                except:
                    continue

            if full_df.empty:
                st.warning(f"⚠️ {name} のデータがテーブルとして抽出できませんでした。")
                continue

            full_df['Date'] = pd.to_datetime(full_df['Date'].astype(str).str.replace('年', '/').str.replace('月', '/').str.replace('日', ''), errors='coerce')
            full_df['Price'] = pd.to_numeric(full_df['Price'].astype(str).str.replace(',', '').str.replace('円', ''), errors='coerce')
            
            full_df = full_df.dropna().drop_duplicates(subset=['Date']).sort_values('Date')
            
            calc_df = full_df[full_df['Date'] >= limit_date_1y].copy()

            if calc_df.empty:
                st.warning(f"⚠️ {name} の有効な日付データがありません。")
                continue

            base_price = calc_df['Price'].iloc[0]
            calc_df['Performance'] = (calc_df['Price'] / base_price) * 100
            
            fund_data_dict[name] = calc_df

        driver.quit()
        status_text_fund.text("投資信託の取得完了！")
        progress_bar_fund.empty()
        
        if fund_data_dict:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            colors = plt.cm.tab10.colors
            max_date = None
            
            for i, (name, df_fund) in enumerate(fund_data_dict.items()):
                color = colors[i % len(colors)]
                ax.plot(df_fund['Date'], df_fund['Performance'], label=name, color=color, linewidth=2)
                
                last_date = df_fund['Date'].iloc[-1]
                last_perf = df_fund['Performance'].iloc[-1]
                last_price = df_fund['Price'].iloc[-1]
                
                if max_date is None or last_date > max_date:
                    max_date = last_date
                
                ax.annotate(f' {int(last_price):,}円', 
                            xy=(last_date, last_perf), 
                            xytext=(5, 0), 
                            textcoords='offset points', 
                            va='center', ha='left', 
                            color=color, fontweight='bold', fontsize=9)
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
            fig.autofmt_xdate()
            
            if max_date is not None:
                ax.set_xlim(left=ax.get_xlim()[0], right=mdates.date2num(max_date + timedelta(days=45)))
                
            ax.set_title("投資信託パフォーマンス比較 (過去1年間)", fontsize=14, fontweight='bold', pad=15)
            ax.set_ylabel("基準価額推移 (1年前の数値を100として計算)", fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.7)
            
            ax.legend(loc='best', fontsize=9, framealpha=0.9)
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    else:
        st.info("投資信託が登録されていません。")

    st.success("すべての処理が完了しました！")

# --- フッター（センタリング表示） ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.85em; margin-bottom: 20px;'>
        ※本アプリが提供するデータは参考情報であり、実際の投資判断は自己責任でお願いいたします。<br>
        © 2026 株価チェックボード All Rights Reserved. 無断複製・転載を禁じます。
    </div>
    """,
    unsafe_allow_html=True
)
