from pydantic import BaseModel, Field

class Equal(BaseModel):
    are_the_strings_equal: bool = Field(False, description="Indicates wether the strings being compared are equal (true) or not (false).")