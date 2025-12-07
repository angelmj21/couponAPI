# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

app = FastAPI(title="Simple Coupon Service")

# ------------------------
# Models
# ------------------------
class DiscountType(str, Enum):
    FLAT = "FLAT"
    PERCENT = "PERCENT"

class Eligibility(BaseModel):
    # User-based
    allowedUserTiers: Optional[List[str]] = None
    minLifetimeSpend: Optional[float] = None
    minOrdersPlaced: Optional[int] = None
    firstOrderOnly: Optional[bool] = None
    allowedCountries: Optional[List[str]] = None

    # Cart-based
    minCartValue: Optional[float] = None
    applicableCategories: Optional[List[str]] = None
    excludedCategories: Optional[List[str]] = None
    minItemsCount: Optional[int] = None

class CouponIn(BaseModel):
    code: str
    description: Optional[str] = ""
    discountType: DiscountType
    discountValue: float = Field(..., gt=0)
    maxDiscountAmount: Optional[float] = None
    startDate: datetime
    endDate: datetime
    usageLimitPerUser: Optional[int] = None
    eligibility: Optional[Eligibility] = None

    @validator("endDate")
    def end_after_start(cls, v, values):
        if "startDate" in values and v < values["startDate"]:
            raise ValueError("endDate must be >= startDate")
        return v

class CouponStored(CouponIn):
    id: str
    usage_count: Dict[str, int] = {}  # userId -> times used

class UserContext(BaseModel):
    userId: str
    userTier: Optional[str] = None
    country: Optional[str] = None
    lifetimeSpend: Optional[float] = 0.0
    ordersPlaced: Optional[int] = 0

class CartItem(BaseModel):
    productId: str
    category: str
    unitPrice: float = Field(..., ge=0)
    quantity: int = Field(..., ge=1)

class Cart(BaseModel):
    items: List[CartItem]

class BestCouponRequest(BaseModel):
    user: UserContext
    cart: Cart

class BestCouponResponse(BaseModel):
    coupon: Optional[Dict[str, Any]] = None
    discountAmount: Optional[float] = None
    reason: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

# ------------------------
# In-memory stores & seed demo user
# ------------------------
coupons: Dict[str, CouponStored] = {}

# Demo hard-coded login user (as requested)
DEMO_USER_EMAIL = "hire-me@anshumat.org"
DEMO_USER_PASSWORD = "HireMe@2025!"

demo_user = {
    "email": DEMO_USER_EMAIL,
    "password": DEMO_USER_PASSWORD,
    "userId": "demo_hireme",
    "userTier": "REGULAR",
    "country": "IN",
    "lifetimeSpend": 10000.0,
    "ordersPlaced": 5
}

# ------------------------
# Helpers
# ------------------------
def now_utc():
    return datetime.now(timezone.utc)

def compute_cart_value(cart: Cart) -> float:
    return sum(item.unitPrice * item.quantity for item in cart.items)

def total_items_count(cart: Cart) -> int:
    return sum(item.quantity for item in cart.items)

def categories_in_cart(cart: Cart) -> List[str]:
    return [item.category for item in cart.items]

def coupon_within_dates(c: CouponStored) -> bool:
    n = now_utc()
    return c.startDate <= n <= c.endDate

def usage_within_limit(c: CouponStored, userId: str) -> bool:
    if c.usageLimitPerUser is None:
        return True
    used = c.usage_count.get(userId, 0)
    return used < c.usageLimitPerUser

def eligibility_satisfied(c: CouponStored, user: UserContext, cart: Cart) -> bool:
    e = c.eligibility
    if e is None:
        return True
    # user-based
    if e.allowedUserTiers and (user.userTier not in e.allowedUserTiers):
        return False
    if e.minLifetimeSpend is not None and (user.lifetimeSpend or 0) < e.minLifetimeSpend:
        return False
    if e.minOrdersPlaced is not None and (user.ordersPlaced or 0) < e.minOrdersPlaced:
        return False
    if e.firstOrderOnly and (user.ordersPlaced or 0) != 0:
        return False
    if e.allowedCountries and (user.country not in e.allowedCountries):
        return False
    # cart-based
    cart_value = compute_cart_value(cart)
    if e.minCartValue is not None and cart_value < e.minCartValue:
        return False
    cart_categories = set(categories_in_cart(cart))
    if e.applicableCategories:
        if not (cart_categories & set(e.applicableCategories)):
            return False
    if e.excludedCategories:
        if cart_categories & set(e.excludedCategories):
            return False
    if e.minItemsCount is not None and total_items_count(cart) < e.minItemsCount:
        return False
    return True

def compute_discount_amount(c: CouponStored, cart_value: float) -> float:
    if c.discountType == DiscountType.FLAT:
        return min(cart_value, c.discountValue)  # can't discount more than cart
    else:  # PERCENT
        raw = (c.discountValue / 100.0) * cart_value
        if c.maxDiscountAmount is not None:
            return min(raw, c.maxDiscountAmount)
        return raw

# ------------------------
# Endpoints
# ------------------------
@app.post("/coupons", response_model=CouponStored)
def create_coupon(coupon: CouponIn):
    code = coupon.code.strip().upper()
    if code in coupons:
        # choice: reject duplicates (documented). Do not overwrite.
        raise HTTPException(status_code=400, detail=f"Coupon code '{code}' already exists.")
    stored = CouponStored(**coupon.dict(), id=str(uuid4()), usage_count={})
    # normalize dates to timezone-aware UTC if naive
    if stored.startDate.tzinfo is None:
        stored.startDate = stored.startDate.replace(tzinfo=timezone.utc)
    if stored.endDate.tzinfo is None:
        stored.endDate = stored.endDate.replace(tzinfo=timezone.utc)
    coupons[code] = stored
    return stored

@app.get("/coupons", response_model=List[CouponStored])
def list_coupons():
    return list(coupons.values())

@app.post("/best-coupon", response_model=BestCouponResponse)
def best_coupon(req: BestCouponRequest):
    user = req.user
    cart = req.cart
    cart_value = compute_cart_value(cart)
    now = now_utc()

    eligible_candidates = []

    for code, c in coupons.items():
        # filter by dates
        if not coupon_within_dates(c):
            continue
        # filter usage limit
        if not usage_within_limit(c, user.userId):
            continue
        # eligibility
        if not eligibility_satisfied(c, user, cart):
            continue
        # compute discount
        discount = compute_discount_amount(c, cart_value)
        # If discount is zero (e.g., cart_value 0), skip
        if discount <= 0:
            continue
        eligible_candidates.append((c, round(float(discount), 2)))

    if not eligible_candidates:
        return BestCouponResponse(coupon=None, discountAmount=0.0, reason="No eligible coupons")

    # Sort by:
    # 1) highest discount (desc)
    # 2) earliest endDate
    # 3) lexicographically smaller code
    def sort_key(pair):
        c, discount = pair
        return (-discount, c.endDate, c.code)

    eligible_candidates.sort(key=sort_key)
    best_c, best_discount = eligible_candidates[0]

    # Return coupon details (mask internal usage_count)
    coupon_out = best_c.dict()
    coupon_out.pop("usage_count", None)
    return BestCouponResponse(coupon=coupon_out, discountAmount=best_discount, reason="OK")

@app.post("/redeem/{code}")
def redeem(code: str, req: BestCouponRequest):
    """
    Simulate a redemption of a coupon for the given user+cart:
    - Validates eligibility same as best-coupon
    - If valid, increments usage_count for that user.
    """
    code = code.strip().upper()
    if code not in coupons:
        raise HTTPException(404, "Coupon not found")
    c = coupons[code]
    user = req.user
    cart = req.cart

    if not coupon_within_dates(c):
        raise HTTPException(400, "Coupon not valid right now (date window)")

    if not usage_within_limit(c, user.userId):
        raise HTTPException(400, "Usage limit reached for this user")

    if not eligibility_satisfied(c, user, cart):
        raise HTTPException(400, "Eligibility criteria not satisfied")

    # compute discount and ensure >0
    discount = compute_discount_amount(c, compute_cart_value(cart))
    if discount <= 0:
        raise HTTPException(400, "Coupon yields zero discount for this cart")

    # Redeem: increment usage
    c.usage_count[user.userId] = c.usage_count.get(user.userId, 0) + 1

    return {"message": "Redeemed", "coupon": c.code, "discountAmount": round(float(discount), 2)}

@app.post("/login")
def login(req: LoginRequest):
    if req.email == demo_user["email"] and req.password == demo_user["password"]:
        return {"ok": True, "user": demo_user}
    raise HTTPException(401, "Invalid credentials")

# Simple seed helper (not an endpoint): add a couple of sample coupons on startup
@app.on_event("startup")
def seed_coupons():
    # only seed if empty
    if coupons:
        return
    from datetime import timedelta
    now = now_utc()
    c1 = CouponIn(
        code="WELCOME100",
        description="₹100 off for new users on cart >= 500",
        discountType=DiscountType.FLAT,
        discountValue=100,
        startDate=now,
        endDate=now + timedelta(days=30),
        usageLimitPerUser=1,
        eligibility=Eligibility(firstOrderOnly=True, minCartValue=500)
    )
    c2 = CouponIn(
        code="GOLD10",
        description="10% off up to ₹500 for GOLD users",
        discountType=DiscountType.PERCENT,
        discountValue=10,
        maxDiscountAmount=500,
        startDate=now,
        endDate=now + timedelta(days=60),
        usageLimitPerUser=None,
        eligibility=Eligibility(allowedUserTiers=["GOLD"], minCartValue=1000)
    )
    c3 = CouponIn(
        code="FASHION5",
        description="5% off on fashion category",
        discountType=DiscountType.PERCENT,
        discountValue=5,
        maxDiscountAmount=None,
        startDate=now,
        endDate=now + timedelta(days=10),
        eligibility=Eligibility(applicableCategories=["fashion"], minItemsCount=1)
    )

    for c in (c1, c2, c3):
        try:
            create_coupon(c)
        except Exception:
            pass