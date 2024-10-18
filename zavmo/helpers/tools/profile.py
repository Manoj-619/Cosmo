from helpers.tools.common import BaseModel, Field, openai

############# required fields ###############
required_fields = ['first_name', 'last_name', 'age', 'edu_level', 'current_role']

class GetFirstName(BaseModel):
    "Return the first name of the user"
    first_name: str = Field(
        description="The first name of the user, often used to address them directly, e.g., 'Diana' or 'John'."
    )

class GetLastName(BaseModel):
    "Return the user's family name or surname"
    last_name: str = Field(
        description="The last name (surname) of the user, typically following the first name, e.g., 'Smith' or 'Haddad'."
    )

class GetAge(BaseModel):
    "Return the user's age"
    age: int = Field(
        description="The age of the user, typically represented in years, e.g., '30' or '25'."
    )

class GetEduLevel(BaseModel):
    "Return the user's education level"
    edu_level: str = Field(
        description="The highest level of education the user has achieved, e.g., 'Bachelor's', 'Master's', 'High School'."
    )

class GetCurrentRole(BaseModel):
    "Return the user's current job role"
    current_role: str = Field(
        description="The specific job position the person is currently in, e.g., 'Software Engineer' or 'Marketing Manager'."
    )

############## profile tools ##############

profile_tools = [GetFirstName, GetLastName, GetAge, GetEduLevel, GetCurrentRole]
tools         = [openai.pydantic_function_tool(i) for i in profile_tools]