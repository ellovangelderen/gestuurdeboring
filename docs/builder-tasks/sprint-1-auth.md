# Builder Task — Sprint 1: Authenticatie & Gebruikersbeheer

**Sprint:** 1 | **Duur:** 1 week | **Afhankelijkheden:** Sprint 0 compleet

---

## Doel

Gebruikers kunnen inloggen. JWT-authenticatie werkt. Rollen worden afgedwongen op alle endpoints.

---

## Wat te bouwen

### Backend

#### `app/models/gebruiker.py`

SQLAlchemy model voor `hdd.gebruikers`:
- `id` (UUID, PK)
- `naam` (str, not null)
- `email` (str, unique, not null)
- `wachtwoord_hash` (str, not null)
- `rol` (enum: `werkvoorbereider`, `engineer`, `beheerder`)
- `actief` (bool, default True)
- `aangemaakt_op` (datetime)
- `gewijzigd_op` (datetime)

#### `app/services/auth_service.py`

- `verifieer_wachtwoord(plain, hashed)` — bcrypt via passlib
- `hash_wachtwoord(plain)` — bcrypt via passlib
- `maak_access_token(data, expires_delta)` — JWT via python-jose, 30 min geldig
- `maak_refresh_token(user_id)` — UUID token, opgeslagen in Redis met TTL 7 dagen
- `verifieer_token(token)` — decoden en valideren
- `invalideer_refresh_token(token)` — verwijderen uit Redis

#### `app/dependencies.py`

- `get_current_user(token: str = Depends(oauth2_scheme), db: Session)` → Gebruiker object of 401
- `require_rol(*rollen)` — dependency factory die 403 gooit als rol niet klopt

#### `app/routers/auth.py`

```
POST /api/v1/auth/login
  Body: {"email": str, "wachtwoord": str}
  Response: {"access_token": str, "token_type": "bearer", "gebruiker": {id, naam, email, rol}}
  Fout: 401 bij ongeldig wachtwoord

POST /api/v1/auth/refresh
  Body: {"refresh_token": str}
  Response: {"access_token": str}
  Fout: 401 bij ongeldig/verlopen refresh token

POST /api/v1/auth/logout
  Auth: Bearer vereist
  Body: {"refresh_token": str}
  Response: {"bericht": "Uitgelogd"}

GET /api/v1/auth/me
  Auth: Bearer vereist
  Response: {id, naam, email, rol}

PUT /api/v1/auth/me/wachtwoord
  Auth: Bearer vereist
  Body: {"huidig_wachtwoord": str, "nieuw_wachtwoord": str}
  Response: {"bericht": "Wachtwoord gewijzigd"}
```

#### `app/routers/gebruikers.py`

Alle endpoints vereisen `beheerder` rol:
```
GET    /api/v1/gebruikers               → lijst van alle gebruikers
POST   /api/v1/gebruikers               → gebruiker aanmaken
GET    /api/v1/gebruikers/{id}          → gebruiker ophalen
PUT    /api/v1/gebruikers/{id}          → gebruiker bijwerken (naam, rol, actief)
DELETE /api/v1/gebruikers/{id}          → deactiveren (niet verwijderen, actief=False)
```

#### Seed script (`app/seed.py`)

Bij eerste start: check of er een beheerder bestaat. Zo niet, maak aan:
- email: uit `.env` (`SEED_ADMIN_EMAIL`)
- wachtwoord: uit `.env` (`SEED_ADMIN_PASSWORD`)
- rol: `beheerder`

Aanroepen in `lifespan` van `main.py` (alleen als `ENVIRONMENT=development` of als `--seed` flag).

#### Tests (`tests/test_auth.py`)

- Login met geldig wachtwoord → 200 + tokens
- Login met ongeldig wachtwoord → 401
- Beveiligd endpoint zonder token → 401
- Beveiligd endpoint met verkeerde rol → 403
- Refresh token flow werkt
- Logout invalideert refresh token

---

### Frontend

#### `src/pages/Login.tsx`

- Email + wachtwoord formulier
- Submit → POST `/api/v1/auth/login`
- Access token opslaan in React context (in-memory, niet localStorage)
- Refresh token opslaan in httpOnly cookie (via `credentials: 'include'`)
- Redirect naar `/projecten` bij succes
- Foutmelding bij verkeerde credentials

#### `src/context/AuthContext.tsx`

- `AuthProvider` component
- State: `user`, `accessToken`, `isLoading`
- Functies: `login()`, `logout()`, `refreshToken()`

#### `src/api/client.ts` (uitbreiden)

- Axios interceptor: voeg `Authorization: Bearer <token>` toe aan elke request
- Axios interceptor: bij 401 response → probeer refresh → retry original request → bij tweede 401 redirect naar login

#### `src/components/ProtectedRoute.tsx`

- Wrappt routes die authenticatie vereisen
- Redirect naar `/login` als niet ingelogd

#### `src/pages/Gebruikers.tsx` (beheerder only)

- Tabel met alle gebruikers (naam, email, rol, actief)
- "Nieuwe gebruiker" knop → modal met formulier
- Rol wijzigen via dropdown in tabel
- Deactiveren via knop

---

## Data in / Data uit

**In:** email + wachtwoord (login)
**Uit:** JWT access token, refresh token (cookie), gebruikersobject

---

## Modules geraakt

- `app/main.py` — seed aanroep toevoegen in lifespan
- `docker-compose.yml` — omgevingsvariabelen voor seed toevoegen

---

## Acceptatiecriteria

- [ ] Werkvoorbereider logt in → redirect naar projectenoverzicht
- [ ] Ongeldige credentials → 401 met melding "Ongeldige inloggegevens"
- [ ] Beveiligd endpoint zonder token → 401
- [ ] Niet-beheerder op `/api/v1/gebruikers` → 403
- [ ] Na 30 minuten: access token verlopen, automatisch vernieuwd via refresh token
- [ ] Uitloggen invalideert refresh token (nieuwe refresh met oud token → 401)
- [ ] Wachtwoorden zijn gehashed in database (nooit plaintext zichtbaar)
- [ ] Seed-beheerder bestaat na eerste `docker compose up`

---

## User Stories

- Epic 7 Must have: "Als gebruiker wil ik kunnen inloggen met een eigen account"
- Epic 7 Must have: "Als beheerder wil ik gebruikers kunnen aanmaken met een rol"
