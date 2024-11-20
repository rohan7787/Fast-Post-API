import database as _database
import models as _models
import sqlalchemy.orm as _orm
import fastapi.security as _security
import schemas as _schemas
import email_validator as _email_validator
import fastapi as _fastapi
import passlib.hash as _hash
import jwt as _jwt

_JWT_SECRET = "irioo923-eii30wlsi30"
oauth2schema = _security.OAuth2PasswordBearer("/api/v1/login")

def create_db():
    return _database.Base.metadata.create_all(bind=_database.engine)


def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def getUserByEmail(email: str, db: _orm.Session):
    return db.query(_models.UserModel).filter(_models.UserModel.email == email).first()


async def create_user(user: _schemas.UserRequest, db: _orm.Session):
    #check for valid email
    try:
        isValid = _email_validator.validate_email(user.email)
        email = isValid.email
    except _email_validator.EmailNotValidError:
        raise _fastapi.HTTPException(
            status_code=400,
            detail="Enter Valid Email Id"
        )

    # Convert normal password to hash
    hashed_password = _hash.bcrypt.hash(user.password)
    # create user model to save in database
    user_obj = _models.UserModel(
        email=user.email, 
        name=user.name,
        phone=user.phone,
        password_hash=hashed_password)
    
    # save user in db
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


async def create_token(user: _models.UserModel):
    # convert user model to schema
    user_schema = _schemas.UserResponse.from_orm(user)
    # convert obj to dict
    user_dict = user_schema.dict()
    del user_dict["created_at"]

    token = _jwt.encode(user_dict, _JWT_SECRET)

    return dict(access_token=token, token_type="bearer")


async def login(email: str, password: str, db: _orm.Session):
    db_user = await getUserByEmail(email=email, db=db)

    # RETURN FALSE WHEN NO EMAIL FOUND
    if not db_user:
        return False
    
    # RETURN FALSE WHEN NO PASSWORD FOUND
    if not db_user.password_verification(password=password):
        return False
    
    return db_user

async def current_user(db: _orm.Session = _fastapi.Depends(get_db),
                   token: str = _fastapi.Depends(oauth2schema)):
    try:
        payload = _jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        # The payload after decode contains id, email, ... which was encoded
        # Get user by Id and Id is available in decoded user payload
        db_user = db.query(_models.UserModel).get(payload["id"])
    except:
        raise _fastapi.HTTPException(status_code=401, detail="Wrong Credentail")
    return _schemas.UserResponse.from_orm(db_user)

async def create_post(user:  _schemas.UserResponse, 
                      db: _orm.Session,
                      post: _schemas.PostRequest):
    post = _models.PostModel(**post.dict(), user_id=user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    # Convert Post model to DTO/SCHEMA and return to API layer
    return  _schemas.PostResponse.from_orm(post)

async def get_posts_by_user(user: _schemas.UserResponse,
                            db: _orm.Session):
    posts = db.query(_models.PostModel).filter_by(user_id=user.id)
    # Convert models to schemas and make a list to return
    return list(map(_schemas.PostResponse.from_orm, posts))

async def get_post_detail(post_id: int, db: _orm.Session):
    db_post = db.query(_models.PostModel).filter(_models.PostModel.id ==  post_id).first()
    if db_post is None:
        raise _fastapi.HTTPException(status_code=404, detail="Post not found")
    # return _schemas.PostResponse.from_orm(db_post)
    return db_post

async def get_user_detail(user_id: int, db: _orm.Session):
    db_user = db.query(_models.UserModel).filter(_models.UserModel.id ==  user_id).first()
    if db_user is None:
        raise _fastapi.HTTPException(status_code=404, detail="User not found")
    return _schemas.UserResponse.from_orm(db_user)

async def delete_post(post: _models.PostModel,  db: _orm.Session):
    db.delete(post)
    db.commit()

async def update_post(post_request: _schemas.PostRequest, 
                      post_model: _models.PostModel,
                      db: _orm.Session):
    post_model.post_title = post_request.post_title
    post_model.post_description = post_request.post_description
    post_model.image = post_request.image
    db.commit()
    db.refresh(post_model)
    return _schemas.PostResponse.from_orm(post_model)

async def get_all_posts(db: _orm.Session):
    posts = db.query(_models.PostModel).all()
    return list(map(_schemas.PostResponse.from_orm, posts))

