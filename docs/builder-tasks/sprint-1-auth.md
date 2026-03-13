# Builder Task — Sprint 1: Authenticatie

**Sprint:** 1 | **Duur:** 0.5 week | **Afhankelijkheden:** Sprint 0 compleet

---

## Doel

Engineers kunnen inloggen. JWT-authenticatie werkt. Iedereen die is ingelogd kan alles — geen rollen in iteratie 1.

> **Gebruikersrollen (werkvoorbereider/engineer/beheerder) worden geïmplementeerd in iteratie 2.**

---

## Wat te bouwen

### Backend

#### `app/core/auth.py`

```python
def hash_wachtwoord(plain: str) -> str:
    """bcrypt via passlib"""

def verifieer_wachtwoord(plain: str, hashed: str) -> bool:
    """bcrypt verificatie"""

def maak_access_token(user_id: str, expires_delta: timedelta = timedelta(hours=8)) -> str:
    """JWT, 8 uur geldig — lang genoeg voor een werkdag zonder re-login"""

def verifieer_token(token: str) -> dict:
    """Decoden en valideren — gooit HTTPException 401 bij fout"""
```

#### `app/core/dependencies.py`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Gebruiker:
    """JWT valideren → gebruiker ophalen → 401 als ongeldig"""

# Geen rol-checks in iteratie 1 — iedereen mag alles
```

#### `app/api/routers/auth.py`

```
POST /api/v1/auth/login
  Body: {"email": str, "wachtwoord": str}
  Response: {"access_token": str, "token_type": "bearer",
             "gebruiker": {id, naam, email}}
  Auth: geen (public)
  Fout: 401 bij ongeldig wachtwoord

GET /api/v1/auth/me
  Auth: Bearer vereist
  Response: {id, naam, email}
```

Geen refresh tokens in iteratie 1 — 8 uur is voldoende voor een werkdag.

#### `app/api/routers/gebruikers.py`

Basis CRUD — geen rolcontrole in iteratie 1:

```
GET    /api/v1/gebruikers        → lijst
POST   /api/v1/gebruikers        → aanmaken
GET    /api/v1/gebruikers/{id}   → ophalen
PUT    /api/v1/gebruikers/{id}   → naam/wachtwoord bijwerken
DELETE /api/v1/gebruikers/{id}   → deactiveren (actief=False)
```

Alle gebruikers worden aangemaakt binnen de huidige workspace (via `get_current_workspace`).

#### Tests (`tests/test_auth.py`)

- Login met geldig wachtwoord → 200 + token
- Login met ongeldig wachtwoord → 401
- Beveiligd endpoint zonder token → 401
- `GET /me` geeft huidig gebruikersobject terug

---

### Frontend

#### `src/pages/Login.tsx`

- Email + wachtwoord formulier
- Submit → POST `/api/v1/auth/login`
- Access token opslaan in React context (in-memory)
- Redirect naar `/projecten` bij succes
- Foutmelding bij foute credentials: "Ongeldig e-mailadres of wachtwoord"

#### `src/context/AuthContext.tsx`

```typescript
interface AuthContext {
  user: { id: string; naam: string; email: string } | null
  accessToken: string | null
  login(email: string, wachtwoord: string): Promise<void>
  logout(): void
}
```

#### `src/api/client.ts`

Axios interceptor: voeg `Authorization: Bearer <token>` toe aan elke request.
Bij 401 response: redirect naar `/login`.

#### `src/components/ProtectedRoute.tsx`

Redirect naar `/login` als niet ingelogd.

---

## Data in / Data uit

**In:** email + wachtwoord
**Uit:** JWT access token (8 uur geldig), gebruikersobject

---

## Modules geraakt

- `app/main.py` — auth en gebruikers routers registreren

---

## Acceptatiecriteria

- [ ] Engineer logt in → redirect naar `/projecten`
- [ ] Ongeldige credentials → 401 met duidelijke melding
- [ ] Beveiligd endpoint zonder token → 401
- [ ] Token geldig voor 8 uur
- [ ] Wachtwoorden gehashed in database (nooit plaintext)
- [ ] Seed admin gebruiker kan inloggen na eerste deployment

---

## User Stories

- Epic 7 Must have: "Als gebruiker wil ik kunnen inloggen met een eigen account"
