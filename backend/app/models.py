"""Domain models for Hospitality — auto-generated from ontology."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

class Person(BaseModel):
    """Entity model for Person."""

    name: str = Field(...)
    email: str | None = None
    role: str | None = None
    description: str | None = None

class Organization(BaseModel):
    """Entity model for Organization."""

    name: str = Field(...)
    description: str | None = None
    industry: str | None = None

class Location(BaseModel):
    """Entity model for Location."""

    name: str = Field(...)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

class Event(BaseModel):
    """Entity model for Event."""

    name: str = Field(...)
    date: datetime | None = None
    description: str | None = None

class Object(BaseModel):
    """Entity model for Object."""

    name: str = Field(...)
    description: str | None = None

class HotelHotelClassEnum(str, Enum):
    ECONOMY = "economy"
    MIDSCALE = "midscale"
    UPSCALE = "upscale"
    UPPER_UPSCALE = "upper_upscale"
    LUXURY = "luxury"

class Hotel(BaseModel):
    """Entity model for Hotel."""

    hotel_id: str = Field(...)
    name: str = Field(...)
    brand: str | None = None
    hotel_class: HotelHotelClassEnum | None = None
    star_rating: float | None = None
    total_rooms: int | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None

class RoomRoomTypeEnum(str, Enum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    SUITE = "suite"
    PENTHOUSE = "penthouse"
    EXECUTIVE = "executive"
    ACCESSIBLE = "accessible"
    CONNECTING = "connecting"

class RoomStatusEnum(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_ORDER = "out_of_order"
    CLEANING = "cleaning"

class RoomViewEnum(str, Enum):
    CITY = "city"
    OCEAN = "ocean"
    GARDEN = "garden"
    POOL = "pool"
    MOUNTAIN = "mountain"
    INTERIOR = "interior"

class Room(BaseModel):
    """Entity model for Room."""

    room_id: str = Field(...)
    room_number: str = Field(...)
    room_type: RoomRoomTypeEnum | None = None
    floor: int | None = None
    max_occupancy: int | None = None
    base_rate: float | None = None
    status: RoomStatusEnum | None = None
    view: RoomViewEnum | None = None

class ReservationReservationStatusEnum(str, Enum):
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class ReservationChannelEnum(str, Enum):
    DIRECT = "direct"
    OTA = "ota"
    CORPORATE = "corporate"
    GROUP = "group"
    WALK_IN = "walk_in"
    LOYALTY = "loyalty"

class Reservation(BaseModel):
    """Entity model for Reservation."""

    reservation_id: str = Field(...)
    check_in: date = Field(...)
    check_out: date = Field(...)
    total_amount: float = Field(...)
    reservation_status: ReservationReservationStatusEnum | None = None
    channel: ReservationChannelEnum | None = None
    special_requests: str | None = None
    num_guests: int | None = None

class GuestLoyaltyTierEnum(str, Enum):
    MEMBER = "member"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    AMBASSADOR = "ambassador"

class GuestGuestTypeEnum(str, Enum):
    LEISURE = "leisure"
    BUSINESS = "business"
    GROUP = "group"
    VIP = "vip"
    LONG_STAY = "long_stay"

class Guest(BaseModel):
    """Entity model for Guest."""

    guest_id: str = Field(...)
    name: str = Field(...)
    email: str | None = None
    phone: str | None = None
    loyalty_tier: GuestLoyaltyTierEnum | None = None
    guest_type: GuestGuestTypeEnum | None = None
    total_stays: int | None = None
    lifetime_value: float | None = None

class ServiceServiceTypeEnum(str, Enum):
    ROOM_SERVICE = "room_service"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    SPA = "spa"
    DINING = "dining"
    LAUNDRY = "laundry"
    TRANSPORT = "transport"
    MAINTENANCE = "maintenance"

class Service(BaseModel):
    """Entity model for Service."""

    service_id: str = Field(...)
    name: str = Field(...)
    service_type: ServiceServiceTypeEnum | None = None
    price: float | None = None
    department: str | None = None
    available_hours: str | None = None
    satisfaction_score: float | None = None

class StaffRoleEnum(str, Enum):
    GENERAL_MANAGER = "general_manager"
    FRONT_DESK = "front_desk"
    HOUSEKEEPING = "housekeeping"
    CONCIERGE = "concierge"
    CHEF = "chef"
    SERVER = "server"
    MAINTENANCE = "maintenance"
    SPA_THERAPIST = "spa_therapist"

class StaffDepartmentEnum(str, Enum):
    FRONT_OFFICE = "front_office"
    HOUSEKEEPING = "housekeeping"
    FOOD_BEVERAGE = "food_beverage"
    SPA = "spa"
    ENGINEERING = "engineering"
    MANAGEMENT = "management"

class StaffShiftEnum(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    ROTATING = "rotating"

class Staff(BaseModel):
    """Entity model for Staff."""

    staff_id: str = Field(...)
    name: str = Field(...)
    role: StaffRoleEnum | None = None
    department: StaffDepartmentEnum | None = None
    hire_date: date | None = None
    shift: StaffShiftEnum | None = None
    performance_rating: float | None = None

