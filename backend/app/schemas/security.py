import uuid
from typing import Literal

from pydantic import StrictInt
from sqlmodel import Field, SQLModel


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of an access JWT. PyJWT validates the signature and time claims;
# these fields validate the claim shape before the request reaches the user DB.
class AccessTokenPayload(SQLModel):
    sub: uuid.UUID
    sid: uuid.UUID
    typ: Literal["access"]
    iss: str
    aud: str
    iat: StrictInt
    nbf: StrictInt
    exp: StrictInt


class PasswordTokenPayload(SQLModel):
    sub: uuid.UUID
    typ: Literal["password_reset", "password_setup"]
    iss: str
    aud: str
    iat: StrictInt
    nbf: StrictInt
    exp: StrictInt
    version: StrictInt


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
