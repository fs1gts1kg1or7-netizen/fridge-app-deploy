from sqlalchemy import create_engine , Column ,Integer , String , Date, select, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import date
from typing import Generator
import datetime
import streamlit as st


#２．ベースクラスの作成(全てのテーブルクラスの土台となるクラス)
Base = declarative_base()

# データベースエンジンを取得する関数
@st.cache_resource(show_spinner=False)
def get_engine():
    # SQLiteデータベースファイルへのパス
    DATABASE_URL = "sqlite:///./refrigerator_app.db"
    # SQLAlchemyのEngineを作成
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
    return engine
#３．セッションの作成（DB操作の窓口）
#データベースとのやり取りは、全てこのSessionを通して行う。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine()) # <-- 新しい定義


class Ingredient(Base):
    #①テーブル名の設定
    __tablename__ = "ingredients"
    #②列の定義
    id = Column(Integer,primary_key = True, index = True)
    name = Column(String, index=True)
    quantity = Column(String)
    use_by_date = Column(Date)
    def __repr__(self):
        return f"<Ingredient(name='{self.name}', quantity='{self.quantity}', use_by_date='{self.use_by_date}')>"

#　アレルギー設定を保存するテーブル  
class Settings(Base):
    __tablename__ = 'settings'
    
    # 1. プライマリキーとなる id を定義（常に1を想定）
    id = Column(Integer, primary_key=True, default=1)
    
    # 2. アレルギー設定の文字列を保存する allergy_text を定義
    allergy_text = Column(String)

# 買い物リストのデータモデル (機能⑤)
class ShoppingItem(Base):
    __tablename__ = "shopping_list"
    
    id = Column(Integer, primary_key = True, index = True )
    # 食材名（例: 醤油、油）
    name = Column(String, index = True)
    # 提案したレシピ名（どの献立のための買い物リストか）
    recipe_name = Column(String) 
    # 登録日時
    created_at = Column(DateTime, default = datetime.datetime.utcnow)
    
# 【🔥🔥追加：レシピ履歴のデータモデル🔥🔥】
class RecipeHistory(Base):
    __tablename__ = "recipe_history"
    
    id = Column(Integer, primary_key=True, index=True)
    # 提案されたレシピ名
    recipe_name = Column(String)
    # 提案されたレシピ全体のテキスト
    full_suggestion = Column(String) 
    # 提案日時
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    
# ====================================================================
# [セッション取得] データベースとのデータのやり取りを開始・終了するための窓口
# ====================================================================
def get_db() -> Generator:
    """データベースセッションを確立し、確実に閉じるための関数（ジェネレーター）"""
    
    # 1. 窓口（セッション）を開く
    db = SessionLocal() 
    
    # 2. 窓口を呼び出し元に渡し、作業を許可（yield）
    try:
        yield db 
        
    # 3. データのやり取りが全て終わったら、確実に窓口を閉じる
    finally:
        db.close()
    
    
# ====================================================================
# [データ操作] 冷蔵庫（DB）に新しい食材を追加する機能
# ====================================================================
def add_ingredient(db:Session, name:str, quantity:str, use_by_date : date):
    """
    新しい食材をデータベースに追加し、追加されたIngredientオブジェクトを返します。
    """
    #1.オブジェクトのインスタンス化(新しい行の作成)
    new_ingredient = Ingredient(name=name, quantity=quantity, use_by_date=use_by_date)
    
    #2.セッションへの追加(窓口にデータ提出)
    db.add(new_ingredient)
    
    # 3. 変更の確定(コミット): これがないとdb.refresh()でエラーになる
    db.commit()
    
    #4.データベースの状態を更新(リフレッシュ)
    db.refresh(new_ingredient)
    
    #5.追加した食材データを呼び出し元に返す
    return new_ingredient

def update_ingredient(db:Session, ingredient_id:int, new_name:str, new_quantity:str, new_use_by_date): 
    """
    特定のIDを持つ食材の情報を更新する。
    """
    #1.更新対象の食材をIDで検索
    ingredient_to_update = db.get(Ingredient, ingredient_id)
    
    #2.食材が見つかったかチェック
    if ingredient_to_update:
        #3.各属性を新しい値に更新
        ingredient_to_update.name = new_name
        ingredient_to_update.quantity = new_quantity
        ingredient_to_update.use_by_date = new_use_by_date
        
        #4.変更の確定(コミット)
        # db.commit() # app.py側で実行されることを想定
        
        # 更新が成功したことを示す True を返す
        return True
    
    # 食材が見つからなかった場合は False を返す
    return False


def get_all_ingredients(db:Session):
    """
    データベース内の全ての食材を取得し、Ingredientsオブジェクトのリストとして返す。
    """
    #1.Select文の作成
    stmt = select(Ingredient)
    
    #2.クエリの実行
    result = db.execute(stmt)
    
    #3.結果の加工と返却
    all_ingredient = result.scalars().all()
    
    return all_ingredient


def delete_ingredient(db:Session, ingredient_id: int)-> bool:
    """
    特定のIDを持つ食材をデータベースから削除する。
    """
    
    #1.削除対象の食材をIDで検索
    ingredient_to_delete = db.get(Ingredient,ingredient_id)
    
    #2.食材が見つかったかチェック
    if ingredient_to_delete:
        #3.セッションから削除(窓口に削除を依頼)
        db.delete(ingredient_to_delete)
        
        #4.上記の変更の確定(コミット)
        # db.commit() # app.py側で実行されることを想定
        
        # 削除が成功したことをしめす　True　を返す
        return True
        
    return False

def update_settings(db: Session, new_allergy_text: str):
    """
    ID=1 の設定行のアレルギー設定を更新する。
    """
    # 1.更新対象の設定行を　ID＝1　で検索
    settings_row = db.get(Settings, 1)
    
    if settings_row:
        # 2.allergy_text を新しい値に更新
        settings_row.allergy_text = new_allergy_text
        # 3.変更の確定(コミット)
        # db.commit() # app.py側で実行されることを想定
        
        return True
    return False


def create_tables():
    """
    データベース内の全てのテーブルを作成する（初回起動時に実行）
    """
    engine = get_engine() 
    # Baseに継承されたすべてのモデル（Ingredients, Settings, ShoppingItem, RecipeHistory）に対応するテーブルをデータベースに作成する
    Base.metadata.create_all(bind=engine)
    

# 買い物リストに追加する関数 
def add_shopping_item(db: Session, name: str, recipe_name: str):
    new_item = ShoppingItem(name=name, recipe_name=recipe_name)
    db.add(new_item)
    # db.commit() # app.py側で実行されることを想定
    
    return new_item

# 買い物リストの全アイテムを取得する関数 
def get_all_shopping_items(db: Session):
    return db.query(ShoppingItem).order_by(ShoppingItem.created_at.desc()).all()

# 買い物リストからアイテムを削除する関数 
def delete_shopping_item(db: Session, item_id: int):
    item = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
    if item:
        db.delete(item)
        # db.commit() # app.py側で実行されることを想定
        
        return True
    return False

# 【🔥🔥追加：レシピ履歴関連の関数🔥🔥】
# レシピ履歴をDBに追加する関数
def add_recipe_history(db: Session, recipe_name: str, full_suggestion: str):
    """
    提案されたレシピを履歴としてデータベースに保存する。
    """
    new_recipe = RecipeHistory(recipe_name=recipe_name, full_suggestion=full_suggestion)
    db.add(new_recipe)
    db.commit() # レシピ履歴はすぐにコミット
    db.refresh(new_recipe)
    return new_recipe

# レシピ履歴を全て取得する関数
def get_all_recipe_history(db: Session):
    """
    データベース内の全てのレシピ履歴を最新順に取得する。
    """
    return db.query(RecipeHistory).order_by(RecipeHistory.created_at.desc()).all()


# レシピ履歴を削除する関数
def delete_recipe_history(db: Session, history_id: int):
    """
    特定のIDを持つレシピ履歴を削除する。
    """
    recipe_to_delete = db.get(RecipeHistory, history_id)
    if recipe_to_delete:
        db.delete(recipe_to_delete)
        # db.commit() は app.py 側で実行されることを想定
        return True
    return False
    
#---------------------------------------------------
#［アプリ起動時の設定］
#---------------------------------------------------
if __name__ == "__main__":
    #1.データベースファイル（refrigerator_app.db）を作成し、テーブルを組み立てる命令を実行
    create_tables()
    
    # 2. Settings テーブルに常に1行のデータが存在するように初期化
    db_init = next(get_db()) # 新しいセッションを取得 (db_initとして命名)
    
    try:
        # Settings テーブルにデータが1行も存在しないか確認
        existing_settings = db_init.query(Settings).filter(Settings.id == 1).first()
        
        if not existing_settings:
            # ID=1 の設定行を空の状態で作成し、DBに保存
            initial_setting = Settings(id=1, allergy_text="")
            db_init.add(initial_setting)
            db_init.commit()
        
    finally:
        db_init.close() # セッションを閉じる
    
    
    
    #2.処理が正常に完了したことを確認するためのメッセージをターミナルに表示
    print("✅データベース refrigerator_app.db が作成され、テーブル構造の準備が完了しました。") 
    
    # 以下の削除テストコードは、データベースが正しく動作することを確認するためのもので、
    # アプリの動作には影響しませんが、エラーが発生しないか確認するために残しておきます。
    db = next(get_db())
    TARGET_ID = 5 
    
    success = delete_ingredient(db,TARGET_ID)
    
    if success:
        db.commit() # テストコードなのでここでコミット
        print(f"✅ ID :{TARGET_ID}の食材を削除しました。")
    else:
        print(f"✖ 削除失敗: ID:{TARGET_ID}の食材は見つかりませんでした。") 
    db.close() # セッションを閉じる