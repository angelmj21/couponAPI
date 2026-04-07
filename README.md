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



