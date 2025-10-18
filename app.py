from openai import OpenAI
import streamlit as st
import pandas as pd 
# database.py から必要な関数をインポート
from database import get_db , get_all_ingredients, add_ingredient
from database import delete_ingredient, create_tables, update_ingredient, Settings, update_settings
# 【🔥🔥インポート追加🔥🔥】
from database import ShoppingItem, add_shopping_item, get_all_shopping_items, delete_shopping_item
from database import RecipeHistory, add_recipe_history, get_all_recipe_history, delete_recipe_history
from sqlalchemy.orm import Session
import random
import time
import datetime # datetimeモジュールは標準ライブラリなのでインポートを維持


# フォームリセット用のキー初期化
if "registration_key" not in st.session_state:
    st.session_state["registration_key"]= str(random.randint(0,100000))
if "deletion_key" not in st.session_state:
    st.session_state["deletion_key"]= str(random.randint(0,100000))
if "update_key" not in st.session_state:
    st.session_state["update_key"] = str(random.randint(0,100000))

# 提案結果保持用のキー
if "last_suggestion" not in st.session_state:
    st.session_state["last_suggestion"] = None # 提案結果を保存
if "proposal_warning" not in st.session_state:
    st.session_state["proposal_warning"] = False


def suggest_menu(ingredients_list, allergy_list, time_constraint = ""):
    """
    登録された食材リストに基づき、ChatGPT (OpenAI API) を使用して献立を提案する
    """
    if not ingredients_list:
        return "冷蔵庫が空です... 😢 まずは食材を登録してください！"
    
    ingredient_details = []
    # 期限が近い順にソート（dateオブジェクトの比較はpd.to_datetimeは不要）
    ingredients_list.sort(key=lambda item: item.use_by_date)
    
    for item in ingredients_list:
        # Dateオブジェクトを文字列に変換して使用
        date_str = item.use_by_date.strftime("%Y/%m/%d") if item.use_by_date else "期限なし"
        ingredient_details.append(
            f"- {item.name} ({item.quantity}) - 期限: {date_str}"
        )
    ingredients_text = "\n".join(ingredient_details)
    
    allergy_instruction = ""
    if allergy_list:
        allergy_str = "、".join(allergy_list)
        allergy_instruction = f"""
        【重要制約】
        以下の食材はアレルギーまたは除外対象です。
        提案するレシピには＊＊これらの食材 {allergy_str}を絶対に使用しないでください。＊＊
        """
    
    prompt = f"""
    あなたは優秀な献立提案AIです。提案は以下のルールを厳守してください。

    ################################################################
    ## 0. 最優先ルール：アレルギー制約 (絶対厳守)
    ################################################################
    
    {allergy_instruction.strip()}
    **いかなる理由があっても、提案するレシピにはアレルギー食材を** *絶対に使用しないでください。*

    ################################################################
    ## 1. 食材使用ルール
    ################################################################
    
    献立提案は、以下に示された【提案に使用する食材リスト】に**リストアップされている食材のみ**を使用して構成してください。
    
    **🔥🔥🔥🔥 最重要指令：リストにある食材は、提案するレシピに** *すべて* **使用しなければなりません。**
    
    ################################################################
    ## 2. 提案の多様性と形式
    ################################################################
    
    - **【提案の強制】** リストに食材が存在する限り、**提案不可メッセージを返すことは許されません。**
    - **【調理法】** 今回の献立は、**煮物、揚げ物、焼き物、蒸し料理**の中から選んでください。炒め物や簡単な和え物に偏らないように、複雑な料理を優先してください。
    
    **🚨【調理時間制約】🚨**
    **{time_constraint}**
    （この制約は「指定なし」の場合、無視して構いません。）
    
    **🚨【買い物リスト用指令】🚨**
    提案するレシピを完成させるために、**冷蔵庫リストに無い**が、**レシピに不可欠**な調味料や副材料（例: 醤油、油、塩、片栗粉など）は、**必ず【不足食材・買い物リスト】のセクションにリストアップしてください。**

    ##################################
    ## 【提案の形式】
    ##################################
    
    以下の手順と形式を厳守してください。
    
    1. **提案名**：レシピ名を太字で魅力的に書く。
    2. **調理法**：レシピの調理法（例：煮物、揚げ物、焼き物、蒸し料理、など）を明記する。
    3. **調理時間**：提案したレシピの目安調理時間を必ず（例：15分）で明記する。
    4. **使用食材**：リストから使用する食材を**すべて**抽出する。
    5. **不足食材・買い物リスト**：提案レシピの調理に必要な、冷蔵庫リストにない**調味料や副材料**を箇条書きでリストアップする。冷蔵庫にある食材は絶対に入れないこと。
    6. **提案理由**：期限が近い食材に言及し、提案した理由を簡潔に述べる。
    7. **調理手順**：具体的な手順を箇条書きで分かりやすく示す。
    
    【提案に使用する食材リスト】
    {ingredients_text}
    """
        
    try:
        # OpenAI APIキーはStreamlit Secretsから取得
        client = OpenAI(api_key=st.secrets["openai"]["api_key"]) 
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優秀な料理専門家です。簡潔で実用的なレシピ提案を作成してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"🚨 献立提案APIの呼び出し中にエラーが発生しました。\n原因: {e}"
        

def display_auto_clear_message(message: str, level: str):
    """
    メッセージを指定されたレベルで表示し、2秒後に自動的に消去する。
    """
    placeholder = st.empty()
    
    if level == "success":
        placeholder.success(message)
    elif level == "warning":
        placeholder.warning(message)
    elif level == "error":
        placeholder.error(message)
    
    # st.time.sleep は非推奨、標準の time.sleep を使用
    time.sleep(2)
    
    placeholder.empty()


def save_allergy_settings():
    """
    アレルギー設定をデータベースに保存する（on_change用）
    """
    with next(get_db()) as db:
        try:
            update_settings(db,st.session_state["allergy_input"])
            db.commit() 
        except Exception as e:
            # エラーログを表示
            st.error(f"アレルギー設定の保存中にエラーが発生しました: {e}")
            pass


def main():
    st.title("献立提案アプリ") 
    st.markdown("---")
    
    # 1. データベースの初期設定と設定読み込み
    create_tables()
    
    # 設定の読み込み
    try:
        db_settings = next(get_db())
        setting_row = db_settings.query(Settings).filter(Settings.id == 1).first()
        if setting_row and 'allergy_input' not in st.session_state:
            st.session_state['allergy_input'] = setting_row.allergy_text
    except Exception as e:
        st.error(f"設定の読み込み中にエラーが発生しました: {e}")
    finally:
        # セッションを確実に閉じる (get_db()でcloseされるが、ここでは明示的に)
        try:
            db_settings.close()
        except:
            pass
        
    
    # 2. 食材の表示エリア (サイドバー)
    st.sidebar.header("現在登録されている食材")
    
    try:
        db=next(get_db())
        ingredients =get_all_ingredients(db)
        
        if ingredients:
            data = [{
                "ID":item.id,
                "食材名":item.name,
                "数量":item.quantity,
                "期限":item.use_by_date
            }
                for item in ingredients 
            ]
            df = pd.DataFrame(data)
            st.sidebar.dataframe(df,use_container_width=True, hide_index = True)
        else:
            st.sidebar.info("提案元となる食材が登録されていません。")
            
    except Exception as e:
        st.sidebar.error(f"データベース接続エラー：{e}")
    finally:
        # db.close() は get_db() の finally ブロックで実行されるが、安全のため残す
        try:
            db.close()
        except:
            pass

    
    # 3. アレルギー設定エリア
    st.header("🚫 アレルギー・除外食材の設定")
    st.markdown("メニュー提案に使用しない食材やアレルギー食材を入力してください。（改行区切り）")
    
    st.text_area(
        "アレルギー、除外食材", placeholder="例: ピーナッツ\n例: えび\n例: 牛乳",
        key="allergy_input",
        on_change = save_allergy_settings 
        )
        
    
    # 4. 食材登録フォームエリア
    st.header("➕ 新しい食材の登録")
    st.markdown("献立提案のための食材を登録してください。")

    with st.form(key=st.session_state['registration_key']):
        new_name = st.text_input("食材名", placeholder="例: 鶏むね肉, 玉ねぎ")
        new_quantity = st.text_input("数量・単位", placeholder="例: 200g, 1個")
        
        # 期限の初期値を今日に設定
        new_use_by_date = st.date_input("賞味期限/消費期限", value=datetime.date.today())

        submit_button = st.form_submit_button(label='食材を登録する 💾')

    if submit_button:
        if new_name and new_quantity:
            try:
                # database.pyのadd_ingredient内でdb.commit()が実行されるため、ここでは不要
                with next(get_db()) as db:
                    add_ingredient(
                        db=db,
                        name=new_name,
                        quantity=new_quantity,
                        use_by_date=new_use_by_date
                    )
                    
                    # 登録成功メッセージを表示
                    display_auto_clear_message(f"『{new_name}』を冷蔵庫に登録しました。", "success")
                
                # フォームリセットと画面更新
                st.session_state["registration_key"]= str(random.randint(0,100000))
                st.rerun()

            except Exception as e:
                display_auto_clear_message(f"食材の登録中にエラーが発生しました: {e}", "error")
                
        else:
            display_auto_clear_message("食材名と数量は必須項目です。", "warning")
            
            
            
    # 5-1. 食材削除フォームエリア
    st.header("➖ 食材の削除")
    st.markdown("削除したい食材のIDを入力してください。IDは左のリストで確認できます。")

    with st.form(key=st.session_state["deletion_key"]):
        delete_id_input = st.number_input(
            "削除したい食材のID", 
            min_value=0,
            step=1,
            value=0
        )
        delete_button = st.form_submit_button(label='食材を削除する 🗑️')

    if delete_button:
        ingredient_id_to_delete = int(delete_id_input)
        success = False 
        
        try:
            with next(get_db()) as db:
                success = delete_ingredient(db, ingredient_id_to_delete)
                
                if success:
                    db.commit() # 削除を確定
                    display_auto_clear_message(f"✅ ID: {ingredient_id_to_delete} の食材を削除しました。", "success")
                else:
                    display_auto_clear_message(f"✖ ID: {ingredient_id_to_delete} の食材は見つかりませんでした。削除は実行されませんでした。", "warning")
            
            if success:
                st.session_state["deletion_key"] = str(random.randint(0,100000))
                st.rerun()
            

        except Exception as e:
            display_auto_clear_message(f"食材の削除中にエラーが発生しました: {e}", "error")
            
            
            
            
    # 5-2. 食材更新フォームエリア
    st.header("🖊️ 食材の更新")
    st.markdown("更新したい食材のIDと新しい情報を入力してください。IDは左のリストで確認できます。")

    with st.form(key = st.session_state["update_key"]):
        update_id_input = st.number_input(
            "更新したい食材のID",
            min_value = 0,
            step = 1,
            value = 0
        )
        update_name = st.text_input("新しい食材名", placeholder = "例：鶏むね肉、玉ねぎ")
        update_quantity = st.text_input("新しい数量、単位", placeholder = " 例：200g、1個")
        update_use_by_date = st.date_input("新しい賞味期限/消費期限", value = datetime.date.today())
        
        update_button = st.form_submit_button(label = "食材を更新する ✏️")
        
    if update_button:
        ingredient_id_to_update = int(update_id_input)
        success = False 
        
        if update_name and update_quantity and update_use_by_date:
            try:
                with next(get_db()) as db:
                    success = update_ingredient(
                        db,
                        ingredient_id_to_update,
                        update_name,
                        update_quantity,
                        update_use_by_date
                    )
                    
                    if success:
                        db.commit() # 更新を確定
                        display_auto_clear_message(f"✅ ID: {ingredient_id_to_update} の食材を更新しました。", "success")
                    else:
                        display_auto_clear_message(f"✖ ID: {ingredient_id_to_update} の食材は見つかりませんでした。更新は実行されませんでした。", "warning")
            
                if success:
                    st.session_state["update_key"] = str(random.randint(0,100000))
                    st.rerun()
                            
            except Exception as e:
                display_auto_clear_message(f"食材の更新中にエラーが発生しました: {e}" , "error")
        else:
            display_auto_clear_message("食材名と数量は必須項目です。", "warning")
        
        
    # アレルギーリストの成形
    allergy_text = st.session_state.get("allergy_input", "")
    allergies_to_exclude = []
    lines = allergy_text.split("\n")

    for item in lines:
        stripped_item = item.strip()
        if stripped_item:
            allergies_to_exclude.append(stripped_item)
    
    # 5-3. 買い物リスト表示・削除エリア (サイドバー)
    st.sidebar.header("📝 買い物リスト")
    
    try:
        db_shopping = next(get_db())
        shopping_items = get_all_shopping_items(db_shopping)

        if shopping_items:
            shopping_data = [{
                "ID": item.id,
                "食材名": item.name,
                "提案元": item.recipe_name
            } for item in shopping_items]
            shopping_df = pd.DataFrame(shopping_data, dtype=object)
            
            st.sidebar.dataframe(shopping_df, use_container_width=True, hide_index=True)

            # 削除フォーム
            with st.sidebar.form(key="delete_shopping_item_form"):
                delete_item_id = st.number_input("削除するID", min_value=0, step=1, value=0)
                delete_item_button = st.form_submit_button("リストから削除 ✖")
                
                if delete_item_button:
                    success_delete = False
                    with next(get_db()) as db_delete:
                        
                        if delete_shopping_item(db_delete, int(delete_item_id)):
                            db_delete.commit() 
                            display_auto_clear_message(f"✅ ID: {delete_item_id} を買い物リストから削除しました。", "success")
                            success_delete = True
                        else:
                            st.sidebar.warning(f"ID: {delete_item_id} はリストに見つかりませんでした。")
                    
                    if success_delete:
                        st.rerun()

        else:
            st.sidebar.info("買い物リストは空です。")
    
    except Exception as e:
        st.sidebar.error(f"買い物リスト表示エラー: {e}")
    finally:
        # db_shopping.close() は get_db() の finally ブロックで実行されるが、安全のため残す
        try:
            db_shopping.close()
        except:
            pass
            
    # 【🔥🔥追加：レシピ履歴エリア (サイドバー)🔥🔥】
    st.sidebar.header("📜 レシピ履歴")

    try:
        db_hist = next(get_db())
        history_items = get_all_recipe_history(db_hist)
        
        if history_items:
            # 履歴をドロップダウンメニューで表示
            history_names = [f"ID:{item.id} - {item.recipe_name} ({item.created_at.strftime('%m/%d %H:%M')})" for item in history_items]
            
            selected_history = st.sidebar.selectbox(
                "閲覧するレシピを選択",
                options=history_names,
                index=0,
                key="selected_recipe_history"
            )
            
            # 選択されたレシピのIDを抽出
            selected_id = int(selected_history.split(" - ")[0].replace("ID:", ""))
            
            # 該当レシピの全文を取得
            selected_recipe = next((item for item in history_items if item.id == selected_id), None)
            
            if selected_recipe:
                # メイン画面に履歴レシピを表示するためのボタン
                if st.sidebar.button("このレシピをメインに表示", key="show_history"):
                    st.session_state["last_suggestion"] = selected_recipe.full_suggestion
                    st.session_state["proposal_warning"] = False
                    st.rerun()

                # 履歴削除機能
                if st.sidebar.button("この履歴を削除 ✖", key="delete_history_item"):
                    with next(get_db()) as db_del_hist:
                        if delete_recipe_history(db_del_hist, selected_id):
                            db_del_hist.commit()
                            display_auto_clear_message(f"✅ ID: {selected_id} のレシピ履歴を削除しました。", "success")
                        else:
                            st.sidebar.warning(f"ID: {selected_id} は見つかりませんでした。")
                    
                    # 削除後、提案表示をクリアしてリラン
                    st.session_state["last_suggestion"] = None 
                    st.rerun()
                    
        else:
            st.sidebar.info("レシピ履歴はありません。")
            
    except Exception as e:
        st.sidebar.error(f"レシピ履歴表示エラー: {e}")
    finally:
        try:
            db_hist.close()
        except:
            pass

    

    # 5-4. 献立提案のための食材選択エリア
    st.header("🛒 提案に使用する食材の選択")

    if ingredients:
        ingredient_names = [item.name for item in ingredients]

        selected_ingredients_names = st.multiselect(
            "提案に使いたい食材を選んでください (複数選択可)",
            options=ingredient_names,
            default=ingredient_names,
            key="selected_ingredients_names_multiselect"
                )
    else:
        st.warning("提案する食材が登録されていません。")
        selected_ingredients_names = []
        
    # 5-5. 調理時間選択エリア
    st.header("⏳ 調理時間の設定")

    cooking_time_option = st.radio(
        "希望する調理時間帯を選択してください。",
        options=["指定なし", "時短（10分以内）", "通常（30分以内）", "本格（30分以上）"],
        index=0,
        key="cooking_time_selection"
    )

    time_constraint_text = ""
    if cooking_time_option == "時短（10分以内）":
        time_constraint_text = "調理時間は**10分以内**で完了することを最優先してください。"
    elif cooking_time_option == "通常（30分以内）":
        time_constraint_text = "調理時間は**30分以内**で完了するレシピを提案してください。"
    elif cooking_time_option == "本格（30分以上）":
        time_constraint_text = "調理時間は**30分以上**かかる、手間をかけた本格的なレシピを提案してください。"

        
        
    # 6. 献立提案エリア
    st.header("🍳 今日の献立提案")
    st.markdown("食材リストの選択状態に基づき、献立を提案します。")


    if st.button("献立を提案してもらう！🤖", key="propose_menu_button"):
        
        # 1. 提案に使用する食材リストの決定
        if not selected_ingredients_names:
            base_ingredients = ingredients
        else:
            base_ingredients = [
                item for item in ingredients 
                if item.name in selected_ingredients_names
            ]

        # アレルギー食材を強制的に除外
        ingredients_for_proposal = [
            item for item in base_ingredients
            if item.name not in allergies_to_exclude
        ]

        # 2. 提案ロジックの実行
        if ingredients_for_proposal:
            with st.spinner("献立を考えています...🤖"):
                suggestion = suggest_menu(
                    ingredients_for_proposal, 
                    allergies_to_exclude, 
                    time_constraint_text
                )
            
            # 【🔥🔥レシピ履歴への保存ロジック🔥🔥】
            try:
                # 提案されたレシピ名を取得
                recipe_line = suggestion.split("1. **提案名**：")
                recipe_name = "提案レシピ"
                if len(recipe_line) > 1:
                    recipe_name = recipe_line[1].split('\n')[0].strip().replace('**', '')

                # DBにレシピ全体とレシピ名を履歴として保存 (database.py内でコミットされる)
                with next(get_db()) as db_hist:
                    add_recipe_history(
                        db_hist, 
                        recipe_name=recipe_name, 
                        full_suggestion=suggestion
                    )
            except Exception as e:
                st.warning(f"レシピ履歴の保存中にエラーが発生しました: {e}") 
            # ------------------------------------
            
            # 【既存のセッションステート保存】
            st.session_state["last_suggestion"] = suggestion
            st.session_state["proposal_warning"] = (
                 len(base_ingredients) != len(ingredients_for_proposal)
            )
            
            # 提案を保存したら、画面をリランして下の表示ロジックへ移行させる
            st.rerun() 
            
        else:
            st.warning("献立提案に必要な食材が冷蔵庫にありません。食材を登録するか、アレルギー設定を確認してください。")

    # ----------------------------------------------------
    # 提案結果の表示ロジック
    # ----------------------------------------------------
    
    suggestion = st.session_state["last_suggestion"]

    if suggestion: # セッションステートに提案結果が残っていれば表示する
        if st.session_state.get("proposal_warning"):
            st.warning("⚠️ 選択された食材の一部にアレルギー・除外食材が含まれていたため、提案から除外されました。")
        
        st.info(suggestion)
        
        # 3. 買い物リストへの追加ロジック 
        shopping_list_marker_candidates = ["不足食材・買い物リスト", "5. 不足食材・買い物リスト"]
        shopping_list_start_index = -1

        for marker in shopping_list_marker_candidates:
            if marker in suggestion:
                shopping_list_start_index = suggestion.find(marker)
                break

        shopping_list_raw = ""
        if shopping_list_start_index != -1:
            start_of_list = suggestion.find('\n', shopping_list_start_index)
            if start_of_list != -1:
                end_marker_candidates = ["提案理由", "調理手順"]
                end_index = len(suggestion)

                for end_marker in end_marker_candidates:
                    current_end_index = suggestion.find(end_marker, start_of_list)
                    if current_end_index != -1 and current_end_index < end_index:
                        end_index = current_end_index
                
                shopping_list_raw = suggestion[start_of_list:end_index].strip()
                
                extracted_items = []
                for line in shopping_list_raw.split('\n'):
                    clean_item = line.strip().lstrip('*- ').strip()
                    if clean_item and clean_item not in ["なし", "特になし"]:
                        extracted_items.append(clean_item)
                
                if extracted_items:
                    with st.expander("🛒 抽出された買い物リストを確認する", expanded=True):
                        st.write("以下の食材を買い物リストに登録しますか？")
                        st.text_area("抽出された食材リスト", "\n".join(extracted_items), height=100, disabled=True)
                        
                        if st.button("このリストを買い物リストに登録する 🛒✨", key="save_shopping_list"):
                            try:
                                with next(get_db()) as db_shop:
                                    recipe_line = suggestion.split("1. **提案名**：")
                                    recipe_name = "提案レシピ"
                                    if len(recipe_line) > 1:
                                        recipe_name = recipe_line[1].split('\n')[0].strip().replace('**', '')

                                    for item_name in extracted_items:
                                        add_shopping_item(db_shop, name=item_name, recipe_name=recipe_name)
                                        
                                    # データベースへの変更を確定
                                    db_shop.commit() 
                                    display_auto_clear_message("✅ 買い物リストに登録しました！サイドバーを確認してください。", "success")

                                # 登録完了後もレシピはクリアしない (st.session_state["last_suggestion"] = None を削除)
                                
                                st.rerun() # リランして画面を更新し、リストを表示

                            except Exception as e:
                                st.error(f"買い物リストの登録中にエラーが発生しました: {e}")
                                
                else:
                    st.success("🎉 献立に必要な追加の食材・調味料は特にありませんでした！")


        
if __name__ == "__main__":
    main()