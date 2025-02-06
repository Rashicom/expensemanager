from fastapi import FastAPI, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import List
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, select, DateTime, func
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy.orm import selectinload

# create async engin
engin = create_async_engine(
    "postgresql+asyncpg://postgres:123@localhost/test",
    echo=True
)

LocalSession = async_sessionmaker(bind=engin)
Base = declarative_base()

async def get_db():
    async with LocalSession() as session:
        return session

# Tables
class Expenses(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    amount = Column(Integer)
    catagory = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class Salary(Base):
    __tablename__ = "salary"
    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Integer, nullable=False)

# pydentic model
class CreateExpenseSchema(BaseModel):
    name:str
    amount:int
    catagory:str

class ExpenseSchema(CreateExpenseSchema):
    id:int
    created_at:datetime

class CreateSalarySchema(BaseModel):
    amount:int

class SalarySchema(CreateSalarySchema):
    id:int
    amount:int


@asynccontextmanager
async def migration_life(app:FastAPI):
    async with engin.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engin.dispose()

app = FastAPI(lifespan=migration_life)

@app.get("/")
async def root():
    return {"status":"ok"}


@app.post("/create-expense", response_model=ExpenseSchema)
async def create_expense(expense:CreateExpenseSchema, db:AsyncSession=Depends(get_db)):
    expense_obj = Expenses(**expense.model_dump())
    db.add(expense_obj)
    await db.commit()
    await db.refresh(expense_obj)                                                                                                           
    return expense_obj


@app.get("/list-all-expense", response_model=List[ExpenseSchema])
async def list_expense(db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Expenses))
    return result.scalars().all()


@app.get("/list-expense", response_model=List[ExpenseSchema])
async def list_expense(
    db: AsyncSession = Depends(get_db),
    start_date: datetime = Query(None, description="Start date for filtering"),
    end_date: datetime = Query(None, description="End date for filtering")
):
    query = select(Expenses)

    # Apply date filtering if parameters are provided
    if start_date and end_date:
        query = query.where(Expenses.created_at.between(start_date, end_date))
    elif start_date:
        query = query.where(Expenses.created_at >= start_date)
    elif end_date:
        query = query.where(Expenses.created_at <= end_date)

    result = await db.execute(query)
    return result.scalars().all()

@app.get("/expense/{expense_id}", response_model=ExpenseSchema)
async def get_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Expenses).where(Expenses.id == expense_id))
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    return expense

@app.get("/list-salary", response_model=List[SalarySchema])
async def list_salary(db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Salary))
    return result.scalars().all()


@app.get("/salary/{id}", response_model=SalarySchema)
async def get_salary(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Salary).where(Salary.id == id))
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(status_code=404, detail="Salary not found")

    return expense

@app.post("/create-slary", response_model=SalarySchema)
async def create_salary(salart:CreateSalarySchema, db:AsyncSession=Depends(get_db)):
    salart_obj = Salary(**salart.model_dump())
    db.add(salart_obj)
    await db.commit()
    await db.refresh(salart_obj)                                                                                                           
    return salart_obj



@app.get("/overview")
async def overview(db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Expenses))
    exps = result.scalars().all()
    sal_result = await db.execute(select(Salary))
    sals = sal_result.scalars().all()
    tot_sal = [sal.amount for sal in sals]
    tot_exp = [exp.amount for exp in exps]
    return {
        "expense_history":tot_exp,
        "salary_history":tot_sal,
        "total_expence":sum(tot_exp),
        "total_salary":sum(tot_sal),
        "remaining":sum(tot_sal)-sum(tot_exp)

    }
    