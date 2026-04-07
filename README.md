1. Project Overview
This project is a FastAPI-based backend service that manages discount coupons and determines the best coupon for a user's cart based on rules like user tier, cart value, categories, and usage limits. It automatically evaluates all eligible coupons and selects the one giving the maximum discount, while respecting constraints such as expiry dates, eligibility conditions, and per-user usage limits.

Built using Python, FastAPI, and Pydantic, the service demonstrates backend API design, business rule implementation, and decision-making logic commonly used in e-commerce platforms. It includes APIs to create coupons, list them, find the best coupon for a cart, and simulate coupon redemption, making it a simple example of a rule-based discount engine.
A lightweight Coupon Engine API that lets businesses create, validate, and redeem discount codes.
Ensures single-use protection using Redis, preventing duplicate redemptions.
Designed to be fast, scalable, and easy to integrate into any e-commerce or billing system.


How to Run:

Prerequisites:
Python 3.11+

Setup:
pip install -r requirements.txt

Start the Service:
uvicorn main:app --reload

5. AI Usage Note
ChatGPT was used to assist with code structuring, debugging, and documenting the project.
Prompts included:
Build a FastAPI project that satisfies the coupon system requirements.
Generate a clean README for my project.


