# HabotConnect — LSA Service Booking Platform (Backend Prototype)

**Candidate Name:** Harshit  
**Position:** Python Backend Developer  
**Date:** August 12, 2026  

---

## 📌 Project Overview & Context
HabotConnect is a digital platform connecting parents with Learning Support Assistants (LSAs) for children with learning difficulties. This repository contains a production-ready, modular RESTful API prototype built on **Python**, **Django**, and **Django REST Framework (DRF)**.

Key Features & Engineering Deliverables:
* **Normalized & Indexed Database Schema:** Entities representing `Parent`, `LearningSupportAssistant`, `Skill`, `Booking`, and `Payment`.
* **High-Performance LSA Search Query:** Optimized endpoint resolving the **N+1 database query problem** via `prefetch_related('skills')`.
* **Robust Double-Booking Prevention:** Serializer validation enforcing mathematical overlap checks ($S_{db} < E_{new} \land E_{db} > S_{new}$).
* **Third-Party Mock Payment Integration:** External integration using Python `requests` with exception handling (`ConnectionError`, `Timeout`) and logging.
* **Automated Webhook Endpoint:** Receives payment events and dynamically updates `Payment` and `Booking` statuses atomically (`SUCCESSFUL` ➔ `CONFIRMED`, `FAILED` ➔ `CANCELLED`).
* **Automated Unit Test Suite:** 6 comprehensive unit tests using DRF's `APITestCase`.
* **CI/CD Integration:** GitHub Actions workflow (`.github/workflows/test.yml`) running automated tests on every push.
* **Interactive Frontend Showcase Dashboard:** A dark-mode UI accessible at `http://127.0.0.1:8000/` for live API testing and demonstration.

---

## 🏗 Architectural Choices: Django MVT vs. Standard MVC

### Django's Native MVT Architecture
Django natively enforces the **Model-View-Template (MVT)** pattern:
* **Model:** Defines database schemas, relationships, indexing, and ORM abstractions.
* **View:** Implements business logic, query execution, and request processing.
* **Template:** Handles presentation rendering (HTML).

### Adaptation for RESTful APIs (DRF Integration)
In pure RESTful microservice architectures, presentation HTML templates are replaced:
* **Serializers:** Take the place of Templates, handling bidirectional translation (Python objects ↔ JSON) and payload validation.
* **ViewSets & `@api_view` Functions:** Route requests, apply HTTP status codes, and return JSON responses.

---

## 🗄 Database Schema Design & Normalization

The schema models 5 normalized relational entities:

```
+------------+       +-------------------+       +-------------------------------+       +-----------+
|   Parent   |       |      Booking      |       |   LearningSupportAssistant    |=======|   Skill   |
+------------+       +-------------------+       +-------------------------------+ (M2M) +-----------+
| id (PK)    |<------| parent (FK)       |       | id (PK)                       |
| name       |       | lsa (FK)          |------>| username (Unique)             |
| email      |       | starttime         |       | email                         |
| phone      |       | endtime           |       | hourly_rate                   |
+------------+       | status            |       | is_active (Indexed)           |
                     +-------------------+       +-------------------------------+
                               |
                               v (1-to-1)
                     +-------------------+
                     |      Payment      |
                     +-------------------+
                     | id (PK)           |
                     | booking (FK)      |
                     | amount            |
                     | txn_ref (Indexed) |
                     | status            |
                     +-------------------+
```

### Database Indexing Strategy
To ensure production performance under scale:
* `is_active` on `LearningSupportAssistant`: Indexed (`Meta.indexes`) for fast filtration of active assistants.
* `starttime` & `endtime` on `Booking`: Indexed to accelerate interval overlap validation queries.
* `transaction_reference` on `Payment`: Indexed (`db_index=True`) for $O(1)$ webhook lookup.

---

## ⚡ Query Optimization: Resolving the N+1 Query Problem

### The N+1 Problem
When retrieving $N$ LSAs and accessing their Many-to-Many `skills` relationship, an unoptimized query performs **1 query** to fetch the LSAs, plus **$N$ additional queries** to fetch skills for each individual LSA ($1 + N$ queries total).

### The Solution: `prefetch_related`
In `GET /api/v1/lsas/search/`, we use `prefetch_related('skills')`:
```python
lsas = LearningSupportAssistant.objects.prefetch_related('skills').filter(is_active=True)
```
* **Query 1:** `SELECT * FROM allinone_learningsupportassistant WHERE is_active = True;`
* **Query 2:** `SELECT * FROM allinone_skills WHERE lsa_id IN (1, 2, 3, ...);`

Regardless of whether there are 5 or 5,000 LSAs, Django executes **exactly 2 queries**.

---

## 🛡 Double-Booking Prevention Logic

To prevent double-booking an LSA for overlapping sessions, `BookingSerializer.validate()` enforces:

$$\text{Existing Start} < \text{Requested End} \quad \text{AND} \quad \text{Existing End} > \text{Requested Start}$$

```python
overlapping_query = Booking.objects.filter(
    lsa=lsa,
    status__in=['PENDING_PAYMENT', 'CONFIRMED'],
    starttime__lt=endtime,
    endtime__gt=starttime
)
if overlapping_query.exists():
    raise serializers.ValidationError({"detail": "The selected LSA is already booked for this time slot."})
```

---

## 🚀 REST API Specifications

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `POST` | `/api/v1/bookings/` | Create a new booking request with overlap validation | `201 Created`, `400 Bad Request` |
| `GET` | `/api/v1/lsas/search/` | Search available LSAs by skill or username (N+1 optimized) | `200 OK`, `404 Not Found` |
| `POST` | `/api/v1/payments/initiate/` | Mock third-party payment gateway integration | `201 Created`, `400 Bad Request` |
| `POST` | `/api/v1/payments/webhook/` | Automated payment success/failure state listener | `200 OK`, `400 Bad Request` |

---

## ⚙️ Setup & Local Installation

1. **Activate Virtual Environment:**
   ```bash
   source venv/bin/activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install django djangorestframework django-filter requests
   ```
3. **Run Migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
4. **Run Server:**
   ```bash
   python manage.py runserver
   ```
5. **Interactive Showcase UI:**
   Open `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running Automated Tests
```bash
python manage.py test
```
All 6 tests in `allinone/tests.py` execute inside an isolated test database and report success.