1. Project Overview
A lightweight Coupon Engine API that lets businesses create, validate, and redeem discount codes.
Ensures single-use protection using Redis, preventing duplicate redemptions.
Designed to be fast, scalable, and easy to integrate into any e-commerce or billing system.

2. Tech Stack
Language: Python 3
Framework: FastAPI
Libraries:
fastapi — API framework
uvicorn — ASGI server
pydantic — request validation
datetime — date/time handling

3. How to Run
Prerequisites:
Python 3.11+
Setup:
pip install -r requirements.txt
Start the Service:
uvicorn main:app --reload

4. AI Usage Note
ChatGPT was used to assist with code structuring, debugging, and documenting the project.
Prompts included:
Build a FastAPI project that satisfies the coupon system requirements.
Generate a clean README for my project.


