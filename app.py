import os
from typing import Optional, List

from fastapi import FastAPI, Body, HTTPException, status, Query, Path
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field, EmailStr
from pydantic.functional_validators import BeforeValidator

from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument


app = FastAPI(
    title="Student Course API",
    summary="A sample application showing how to use FastAPI to add a ReST API to a MongoDB collection.",
)
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.college
student_collection = db.get_collection("students")

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]


class Address(BaseModel):
    """
    Container for address information.
    """
    city: str
    country: str


class StudentData(BaseModel):
    """
    Data object containing name and age of a student.
    """
    name: str
    age: int


class StudentModel2(BaseModel):
    """
    Container for a single student record.
    """

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    age: int = Field(...)
    address: Address
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "string",
                "age": 0,
                "address": {
                    "city": "string",
                    "country": "string"
                }
            }
        },
    )


class NewStudentResponse(BaseModel):
    """
    Response model for newly created student record.
    """
    id: str


class UpdateStudentModel2(BaseModel):
    """
    A set of optional updates to be made to a document in the database.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: Optional[str] = None
    age: Optional[int] = None
    address: Optional[Address] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "string",
                "age": 0,
                "address": {
                    "city": "string",
                    "country": "string",
                }
            }
        }
    )


# class StudentModel(BaseModel):
#     """
#     Container for a single student record.
#     """

#     # The primary key for the StudentModel, stored as a `str` on the instance.
#     # This will be aliased to `_id` when sent to MongoDB,
#     # but provided as `id` in the API requests and responses.
#     id: Optional[PyObjectId] = Field(alias="_id", default=None)
#     name: str = Field(...)
#     email: EmailStr = Field(...)
#     course: str = Field(...)
#     gpa: float = Field(..., le=4.0)
#     model_config = ConfigDict(
#         populate_by_name=True,
#         arbitrary_types_allowed=True,
#         json_schema_extra={
#             "example": {
#                 "name": "Jane Doe",
#                 "email": "jdoe@example.com",
#                 "course": "Experiments, Science, and Fashion in Nanophotonics",
#                 "gpa": 3.0,
#             }
#         },
#     )


# class UpdateStudentModel(BaseModel):
#     """
#     A set of optional updates to be made to a document in the database.
#     """

#     name: Optional[str] = None
#     email: Optional[EmailStr] = None
#     course: Optional[str] = None
#     gpa: Optional[float] = None
#     model_config = ConfigDict(
#         arbitrary_types_allowed=True,
#         json_encoders={ObjectId: str},
#         json_schema_extra={
#             "example": {
#                 "name": "Jane Doe",
#                 "email": "jdoe@example.com",
#                 "course": "Experiments, Science, and Fashion in Nanophotonics",
#                 "gpa": 3.0,
#             }
#         },
#     )


# class StudentCollection(BaseModel):
#     """
#     A container holding a list of `StudentModel` instances.

#     This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
#     """

#     students: List[StudentModel]


@app.post(
    "/students/",
    response_description="A JSON response sending back the ID of the newly created student record.",
    response_model=StudentModel2,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def create_student(student: StudentModel2 = Body(...)):
    """
    API to create a student in the system. All fields are mandatory and required while creating the student in the system.
    """
    new_student = await student_collection.insert_one(
        student.model_dump(by_alias=True, exclude=["id"])
    )
    created_student = await student_collection.find_one(
        {"_id": new_student.inserted_id}
    )
    return created_student


@app.get(
    "/students/",
    response_description="sample response",
    response_model=List[StudentData],
    response_model_by_alias=False,
)
async def list_students(country: Optional[str] = Query(None, description="To apply filter of country. If not given or empty, this filter should be applied."),
                        age: Optional[int] = Query(None, description="Only records which have age greater than equal to the provided age should be present in the result. If not given or empty, this filter should be applied.")):
    """
    An API to find a list of students. You can apply filters on this API by passing the query parameters as listed below.
    """
    # Prepare filter conditions
    filter_conditions = {}
    if country:
        filter_conditions["address.country"] = country
    if age is not None:
        filter_conditions["age"] = {"$gte": age}

    # Fetch students from database based on filter conditions
    students_cursor = student_collection.find(filter_conditions)

    # Convert cursor to list of dictionaries
    students_data = []
    async for student in students_cursor:
        students_data.append(student)

    # Construct and return list of StudentData objects
    return [
        StudentData(name=student["name"], age=student["age"])
        for student in students_data
    ]


# @app.get(
#     "/students/",
#     response_description="List all students",
#     response_model=StudentCollection,
#     response_model_by_alias=False,
# )
# async def list_students():
#     """
#     List all of the student data in the database.

#     The response is unpaginated and limited to 1000 results.
#     """
#     return StudentCollection(students=await student_collection.find().to_list(1000))


@app.get(
    "/students/{id}",
    response_description="sample response",
    response_model=StudentModel2,
    response_model_by_alias=False,
)
async def fetch_student(id: str = Path(..., description="The ID of the student previously created.")):

    if (
        student := await student_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return student

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


# @app.put(
#     "/students/{id}",
#     response_description="Update a student",
#     response_model=StudentModel,
#     response_model_by_alias=False,
# )
# async def update_student(id: str, student: UpdateStudentModel = Body(...)):
#     """
#     Update individual fields of an existing student record.

#     Only the provided fields will be updated.
#     Any missing or `null` fields will be ignored.
#     """
#     student = {
#         k: v for k, v in student.model_dump(by_alias=True).items() if v is not None
#     }

#     if len(student) >= 1:
#         update_result = await student_collection.find_one_and_update(
#             {"_id": ObjectId(id)},
#             {"$set": student},
#             return_document=ReturnDocument.AFTER,
#         )
#         if update_result is not None:
#             return update_result
#         else:
#             raise HTTPException(
#                 status_code=404, detail=f"Student {id} not found")

#     # The update is empty, but we should still return the matching document:
#     if (existing_student := await student_collection.find_one({"_id": id})) is not None:
#         return existing_student

#     raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.patch(
    "/students/{id}",
    response_description="No content",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_student(id: str, student: UpdateStudentModel2 = Body(...)):
    """
    API to update the student's properties based on information provided.
    Not mandatory that all information would be sent in PATCH, only what fields are sent should be updated in the Database.
    """
    # Check if student with given ID exists
    existing_student = await student_collection.find_one({"_id": ObjectId(id)})
    if not existing_student:
        raise HTTPException(status_code=404, detail=f"Student {id} not found")

    # Convert the student model to a dictionary using model_dump
    student_data = student.model_dump(by_alias=True)

    # Filter out None values
    student_data = {k: v for k, v in student_data.items() if v is not None}

    # Update the student record in the database
    await student_collection.update_one({"_id": ObjectId(id)}, {"$set": student_data})

    # Return 204 No Content response
    return Response(status_code=status.HTTP_204_NO_CONTENT, content=None)


@app.delete("/students/{id}", response_description="sample response")
async def delete_student(id: str):
    delete_result = await student_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Student {id} not found")
