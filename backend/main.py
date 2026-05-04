from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, database
import utils
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError


models.Base.metadata.create_all(bind=database.engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()

def get_db():
    db = database.SessionLocal() # 1. make a new database session (Connection) for each request that comes to the API.
    try:
        yield db    # 2. In this line we are yielding the database session to the API endpoint functions that depend on it.
    finally:
        db.close()  # 3. End of the api workflow, it will work again from here and close the database connection (session) that we opened in step 1.


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"},
    )

    try:
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# Project
@app.post("/projects/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # new method to convert Pydantic model to dict and unpack it to create SQLAlchemy model instance
    db_project = models.Project(**project.model_dump(), owner_Id=current_user.id)  

    # old method to create SQLAlchemy model instance
    # db_project = models.Project(
    #     title=project.title,
    #     description=project.description,
    #     tech_stack=project.tech_stack,
    #     github_link=project.github_link,
    #     image_url=project.image_url
    # )

    db.add(db_project)
    db.commit() 
    db.refresh(db_project) 
    return db_project


@app.get("/projects/", response_model=list[schemas.Project])
def get_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()


@app.delete("/projects/{project_id}")
def delete_project(
    project_id:int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if db_project is None:
        raise HTTPException(status_code=404, detail="Project Not Found")
    
    if db_project.owner_Id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions (This isn't your project!)"
        )
    
    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}


@app.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int, 
    updated_data: schemas.ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if db_project.owner_Id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions (This isn't your project!)"
        )

    update_dict = updated_data.model_dump()
    for key, value in update_dict.items():
        setattr(db_project, key, value) 

    db.commit()
    db.refresh(db_project)
    return db_project


# User
@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pwd = utils.hash_password(user.password)

    new_user = models.User(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = utils.create_access_token(data = {"sub":user.username})

    return {"access_token": access_token, "token_type": "bearer"}
