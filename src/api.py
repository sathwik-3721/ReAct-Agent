# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field
# from typing import List
# from react.agent import agent, IterationStep  # Import only the agent instance and IterationStep model


# app = FastAPI()


# class QueryRequest(BaseModel):
#     query: str = Field(..., description="The query to execute.")


# @app.post("/execute/", response_model=List[IterationStep])
# async def execute_query(request: QueryRequest):
#     """
#     Executes a query through the agent and returns the list of iteration steps.
#     """
#     try:
#         iterations = agent.execute(request.query)
#         return iterations
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


# @app.get("/health")
# async def health_check():
#     """
#     Check if api is working.
#     """
#     return {"status": "ok"}

# FastAPI code
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel, Field
# from typing import AsyncGenerator
# from react.agent import agent, IterationStep  # Import only the agent instance and IterationStep model
# import json
# import asyncio

# app = FastAPI()

# class QueryRequest(BaseModel):
#     query: str = Field(..., description="The query to execute.")

# async def generate_iterations(query: str) -> AsyncGenerator[str, None]:
#     try:
#         iterations = agent.execute(query)
#         # yield f"data: {json.dumps(iterations)}\n\n"
#         async for iteration in iterations:  # Assuming execute_stream is an async generator
#             yield f"data: {json.dumps(iteration.dict())}\n\n"
#             await asyncio.sleep(1)  # Simulate delay if needed
#     except Exception as e:
#         yield f"data: {json.dumps({'error': str(e)})}\n\n"

# @app.post("/execute/")
# async def execute_query_stream(request: QueryRequest):
#     """
#     Executes a query through the agent and streams iteration steps.
#     """
#     return StreamingResponse(generate_iterations(request.query), media_type="text/event-stream")

# @app.get("/health")
# async def health_check():
#     """
#     Check if API is working.
#     """
#     return {"status": "ok"}


# Flask code for API
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, Field, ValidationError
from react.agent import agent, IterationStep
import json
import asyncio
import inspect
import collections.abc

app = Flask(__name__)
CORS(app)  # Enable CORS if needed

# Define input schema using Pydantic
class QueryRequest(BaseModel):
    query: str = Field(..., description="The query to execute.")

# Generator for server-sent events
def generate_iterations(query: str):
    try:
        result = agent.execute(query)
        print("DEBUG: Result type:", type(result))
        print("DEBUG: Result:", result)

        # Case 1: If result is an async generator
        if inspect.isasyncgen(result):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def iterate():
                async for item in result:
                    yield f"data: {json.dumps(item.dict())}\n\n"
                    await asyncio.sleep(1)

            agen = iterate()
            while True:
                try:
                    chunk = loop.run_until_complete(agen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break

        # Case 2: If result is a regular iterable (like list)
        elif isinstance(result, collections.abc.Iterable):
            for item in result:
                yield f"data: {json.dumps(item.dict())}\n\n"

        else:
            yield f"data: {json.dumps({'error': 'Unsupported result type'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route("/execute/", methods=["POST"])
def execute_query_stream():
    try:
        data = request.get_json()
        validated = QueryRequest(**data)
        return Response(generate_iterations(validated.query), mimetype='text/event-stream')
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, threaded=True)

# # Code with JSON response and no SSE
# from flask import Flask, Response, request, jsonify
# from flask_cors import CORS
# from pydantic import BaseModel, Field, ValidationError
# from react.agent import agent, IterationStep
# import json
# import asyncio
# import inspect
# import collections.abc

# app = Flask(__name__)
# CORS(app)  # Enable CORS if needed

# # Pydantic input schema
# class QueryRequest(BaseModel):
#     query: str = Field(..., description="The query to execute.")

# # Execute query and return all iterations at once
# def run_agent(query: str):
#     try:
#         result = agent.execute(query)
#         output = []

#         # Case 1: If async generator
#         if inspect.isasyncgen(result):
#             async def collect_async():
#                 async for item in result:
#                     output.append(item.dict())
#             asyncio.run(collect_async())

#         # Case 2: If synchronous iterable
#         elif isinstance(result, collections.abc.Iterable):
#             for item in result:
#                 output.append(item.dict())

#         # Case 3: Single result
#         else:
#             output.append({"result": str(result)})

#         return output

#     except Exception as e:
#         return [{"error": str(e)}]

# @app.route("/execute/", methods=["POST"])
# def execute_query():
#     try:
#         data = request.get_json()
#         validated = QueryRequest(**data)
#         result = run_agent(validated.query)
#         return jsonify(result)
#     except ValidationError as e:
#         return jsonify({"error": e.errors()}), 422

# @app.route("/health", methods=["GET"])
# def health_check():
#     return jsonify({"status": "ok"})

# if __name__ == "__main__":
#     app.run(debug=True, threaded=True)
