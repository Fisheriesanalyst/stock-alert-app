import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import time
import json
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import japanize_matplotlib

# --- デフォルトの銘柄データ ---
default_data = [
    {"区分": "個別株", "銘柄名": "極洋", "コード": "1301.T"},
    {"区分": "個別株", "銘柄名": "ディー・エヌ・エー", "コード": "2432.T"},
    {"区分": "個別株", "銘柄名": "キッコーマン", "コード": "2801.T"},
    {"区分": "個別株", "銘柄名": "日本たばこ産業", "コード": "2914.T"},
    {"区分": "個別株", "銘柄名": "花王", "コード": "4452.T"},
    {"区分": "個別株", "銘柄名": "武田薬品工業", "コード": "4502.T"},
    {"区分": "個別株", "銘柄名": "クリエートメディック", "コード": "5187.T"},
    {"区分": "個別株", "銘柄名": "イオン", "コード": "8267.T"},
    {"区分": "個別株", "銘柄名": "セブン銀行", "コード": "8410.T"},
    {"区分": "個別株", "銘柄名": "野村ホールディングス", "コード": "8604.T"},
    {"区分": "個別株", "銘柄名": "京浜急行電鉄", "コード": "9006.T"},
    {"区分": "個別株", "銘柄名": "アッヴィ", "コード": "ABBV"},
    {"区分": "個別株", "銘柄名": "アトランティック", "コード": "AUB"},
    {"区分": "個別株", "銘柄名": "バタフライ・ネットワーク", "コード": "BFLY"},
    {"区分": "個別株", "銘柄名": "ダウ・インク(売却済30.99）", "コード": "DOW"},
    {"区分": "個別株", "銘柄名": "エンブリッジ", "コード": "ENB"},
    {"区分": "個別株", "銘柄名": "キンバリー・クラーク", "コード": "KMB"},
    {"区分": "個別株", "銘柄名": "コカ・コーラ", "コード": "KO"},
    {"区分": "個別株", "銘柄名": "ニュートリエン", "コード": "NTR"},
    {"区分": "個別株", "銘柄名": "リオティント", "コード": "RIO"},
    {"区分": "個別株", "銘柄名": "リカージョン", "コード": "RXRX"},
    {"区分": "個別株", "銘柄名": "SFL", "コード": "SFL"},
    {"区分": "個別株", "銘柄名": "シリウス", "コード": "SIRI"},
    {"区分": "個別株", "銘柄名": "ベライゾン", "コード": "VZ"},
    {"区分": "個別株", "銘柄名": "スペースX", "コード": "SPCX"},
    {"区分": "個別株", "銘柄名": "ガリアーノ・ゴールド", "コード": "GAU"},
    {"区分": "個別株", "銘柄名": "Global米国優先証券(売却済18.9)", "コード": "PFFD"},
    {"区分": "個別株", "銘柄名": "BSシニアローン(売却済40.4）", "コード": "SRLN"},
    {"区分": "投資信託", "銘柄名": "インベスコ 世界厳選株式＜H無＞", "コード": "18312991"},
    {"区分": "投資信託", "銘柄名": "グロース・オポチュニティD", "コード": "32314233"},
    {"区分": "投資信託", "銘柄名": "ノムラ･ジャパン･オープン", "コード": "01311962"}
]

# --- 画面設定 ---
st.set_page_config(page_title="株価・投資信託 チェックボード", layout="wide")

# タイトルをセンタリング表示（HTMLのh3タグとcenterタグを使用）
st.markdown("<h3 style='text-align: center;'>📊 株価・投資信託 チェックボード</h3>", unsafe_allow_html=True)

# --- 画像と説明文の表示 ---
try:
    st.image("25rule_minimized.jpg", use_container_width=True)
except Exception:
    st.warning("画像ファイル「25rule_minimized.jpg」が読み込めません。GitHubへのアップロードを確認してください。")

st.info("""
**💡 株式投資における「25%ルール」**\n
「直近の最高値から株価が25%以上下落した時点で売却（損切り・利益確定）を検討する」というシンプルな原則です。値上がり局面での早すぎる利益確定を防ぎつつ、急落時には逃げ遅れを回避し、大切な資産を守る効果が期待できます。\n
本アプリでは、登録した保有銘柄の「過去1年間の最高値」を基準に現在の下落率を自動計算し、（15%未満＝基準内、15～25%＝-15%、25％以上＝-25%以上）の3段階でアラートを表示します。日々の投資判断のサポートとしてご活用ください。
""")

# --- セッション（一時記憶）の初期化 ---
if 'portfolio' not in st.session_state:
    st.session_state['portfolio'] = pd.DataFrame(default_data)

# --- 1. 銘柄の管理機能 ---
st.markdown("#### 1. 銘柄の登録・管理")
st.markdown("下の表を直接クリックして銘柄を追加・編集・削除できます。別の端末で使う場合は「エクスポート」でファイルを保存し、「インポート」で読み込んでください。")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📂 JSONファイルをインポート", type="json")
    if uploaded_file is not None:
        try:
            imported_data = json.load(uploaded_file)
            st.session_state['portfolio'] = pd.DataFrame(imported_data)
            st.success("データをインポートしました！")
        except Exception as e:
            st.error("インポートに失敗しました。ファイル形式を確認してください。")

with col2:
    export_json = st.session_state['portfolio'].to_json(orient='records', force_ascii=False)
    st.download_button(
        label="💾 現在のデータをエクスポート",
        data=export_json,
        file_name="portfolio_data.json",
        mime="application/json",
    )

edited_df = st.data_editor(
    st.session_state['portfolio'],
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
        st.dataframe(pd.DataFrame(results), use_container_width=True)

        if alerts:
            st.error("### 📉 25%下落アラート\n" + "\n".join(alerts))
        else:
            st.success("現在、直近高値から25%以上下落している個別銘柄はありません。")
    else:
        st.info("個別株が登録されていません。")

    st.markdown("---")

    # ========================================
    # 投資信託チェック
    # ========================================
    st.markdown("##### 投資信託")
    
    if len(funds) > 0:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        status_text_fund = st.empty()
        progress_bar_fund = st.progress(0)
        total_funds = len(funds)
        
        limit_date_1y = datetime.now() - timedelta(days=365)
        limit_date_6m = datetime.now() - timedelta(days=180)

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        for i, (name, code) in enumerate(funds.items()):
            status_text_fund.text(f"投資信託取得中... {name} ({i+1}/{total_funds})")
            progress_bar_fund.progress((i + 1) / total_funds)
            
            url = f"https://finance.yahoo.co.jp/quote/{str(code).strip()}/history"
            driver.get(url)
            time.sleep(4)
            
            all_html = []
            for page in range(20):
                all_html.append(driver.page_source)
                try:
                    next_btn = driver.find_element(By.XPATH, "//*[contains(text(), '次へ')]")
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
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
            calc_df = full_df[full_df['Date'] >= limit_date_1y]

            if calc_df.empty:
                st.warning(f"⚠️ {name} の有効な日付データがありません。")
                continue

            high_1y = calc_df['Price'].max()
            current_price = calc_df['Price'].iloc[-1]
            drop_rate = (current_price - high_1y) / high_1y * 100

            plot_df = calc_df[calc_df['Date'] >= limit_date_6m]

            if plot_df.empty:
                st.warning(f"⚠️ {name} の過去6ヶ月分のデータがありません。")
                continue

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(plot_df['Date'], plot_df['Price'], marker='o', markersize=3, linestyle='-', color='#1f77b4')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            fig.autofmt_xdate()
            
            ax.set_title(f"{name} - 基準価額の推移 (過去6ヶ月)", fontsize=14, fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.7)
            
            last_date = plot_df['Date'].iloc[-1]
            ax.annotate(f' {int(current_price):,}', xy=(last_date, current_price), xytext=(5, 0), textcoords='offset points', va='center', ha='left', color='#1f77b4', fontweight='bold', fontsize=11)

            text_str = f"1年以内高値: {int(high_1y):,}円\n現在値: {int(current_price):,}円\n下落率: {drop_rate:.2f}%"
            props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray')
            ax.text(0.02, 0.95, text_str, transform=ax.transAxes, fontsize=10, verticalalignment='top', horizontalalignment='left', bbox=props)
            ax.set_xlim(plot_df['Date'].min(), last_date + timedelta(days=15))
            
            with st.expander(f"{name} の推移を見る", expanded=True):
                st.pyplot(fig)
            plt.close()

        driver.quit()
        status_text_fund.text("投資信託の取得完了！")
    else:
        st.info("投資信託が登録されていません。")

    st.success("すべての処理が完了しました！")
