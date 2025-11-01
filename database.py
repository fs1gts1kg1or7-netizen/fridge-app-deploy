from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import date
from typing import Generator
import datetime
import streamlit as st

# =======================================
# 1. ベースクラスの作成
# =======================================
Base = declarative_base()

# =======================================
# 2. データベースエンジン
# =======================================
@st.cache_resource(show_spinner=False)
def get_engine():
    DATABASE_URL = "sqlite:///./refrigerator_app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    return engine

# =======================================
# 3. セッション作成
# =======================================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

# =======================================
# 4. モデル定義
# =======================================
class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(String)
    use_by_date = Column(Date)

    def __repr__(self):
        return f"<Ingredient(name='{self.name}', quantity='{self.quantity}', use_by_date='{self.use_by_date}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "use_by_date": self.use_by_date.isoformat() if self.use_by_date else None
        }

class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True, default=1)
    allergy_text = Column(String)

    def to_dict(self):
        return {"id": self.id, "allergy_text": self.allergy_text}

class ShoppingItem(Base):
    __tablename__ = "shopping_list"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    recipe_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "recipe_name": self.recipe_name,
            "created_at": self.created_at.isoformat()
        }

class RecipeHistory(Base):
    __tablename__ = "recipe_history"
    id = Column(Integer, primary_key=True, index=True)
    recipe_name = Column(String)
    full_suggestion = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "recipe_name": self.recipe_name,
            "full_suggestion": self.full_suggestion,
            "created_at": self.created_at.isoformat()
        }

# =======================================
# 5. DBセッション取得
# =======================================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =======================================
# 6. CRUD関数（commitオプション付き）
# =======================================
def add_ingredient(db: Session, name: str, quantity: str, use_by_date: date, commit: bool = True):
    new_ingredient = Ingredient(name=name, quantity=quantity, use_by_date=use_by_date)
    db.add(new_ingredient)
    if commit:
        db.commit()
        db.refresh(new_ingredient)
    return new_ingredient

def update_ingredient(db, ingredient_id: int, new_name: str, new_quantity: str, new_use_by_date: datetime.date, commit: bool = True):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient:
        ingredient.name = new_name
        ingredient.quantity = new_quantity
        ingredient.use_by_date = new_use_by_date
        
        if commit:
            db.commit()
        return True
    return False


def delete_ingredient(db, ingredient_id: int, commit: bool = True):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient:
        db.delete(ingredient)
        if commit:
            db.commit()
        return True
    return False


def get_all_ingredients(db: Session):
    stmt = select(Ingredient)
    return db.execute(stmt).scalars().all()

def update_settings(db: Session, new_allergy_text: str, commit: bool = True):
    settings = db.get(Settings, 1)
    if not settings:
        return False
    settings.allergy_text = new_allergy_text
    if commit:
        db.commit()
    return True

# 【新規追加】買い物リストに追加する関数。これが欠落していたためエラーが発生していました。
def add_shopping_item(db: Session, name: str, recipe_name: str, commit: bool = True):
    new_item = ShoppingItem(name=name, recipe_name=recipe_name)
    db.add(new_item)
    if commit:
        db.commit()
    return new_item


def delete_shopping_item(db, item_id: int, commit: bool = True):
    item = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
    if item:
        db.delete(item)
        if commit:
            db.commit()
        return True
    return False

def get_all_shopping_items(db: Session):
    return db.query(ShoppingItem).order_by(ShoppingItem.created_at.desc()).all()

def add_recipe_history(db: Session, recipe_name: str, full_suggestion: str, commit: bool = True):
    new_history = RecipeHistory(recipe_name=recipe_name, full_suggestion=full_suggestion)
    db.add(new_history)
    if commit:
        db.commit()
    return new_history

def delete_recipe_history(db, history_id: int, commit: bool = True):
    item = db.query(RecipeHistory).filter(RecipeHistory.id == history_id).first()
    if item:
        db.delete(item)
        if commit:
            db.commit()
        return True
    return False

def get_all_recipe_history(db: Session):
    return db.query(RecipeHistory).order_by(RecipeHistory.created_at.desc()).all()

def clear_shopping_list(db: Session, commit: bool = True):
    """買い物リストの項目を全て削除する"""
    try:
        # ShoppingItem モデルのすべてのレコードを削除
        db.query(ShoppingItem).delete()
        if commit:
            db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

# =======================================
# 7. テーブル作成
# =======================================
def create_tables():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

# =======================================
# 8. 初期化処理
# =======================================
if __name__ == "__main__":
    create_tables()
    db_init = next(get_db())
    try:
        if not db_init.query(Settings).filter(Settings.id == 1).first():
            db_init.add(Settings(id=1, allergy_text=""))
            db_init.commit()
    finally:
        db_init.close()
    print("✅ データベース初期化完了")