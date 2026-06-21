# Walkthrough - Development Progress

This walkthrough documents the verified implementations of the Carbon Footprint gamified app.

---

## Phase 1: Database Architecture & Core Roles

We have successfully implemented the database schema, models, and authentication logic for the Carbon Footprint application.

### Changes Made

1. **[requirements.txt](file:///e:/promptwar/requirements.txt)**
   - Added core dependencies: Flask, Flask-SQLAlchemy, Flask-Login, PyMySQL, python-dotenv, and cryptography.

2. **[config.py](file:///e:/promptwar/config.py)**
   - Configured key settings like `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI`.
   - Setup fallback to local SQLite (`sqlite:///app.db`) for simplified development and testing.

3. **[database.py](file:///e:/promptwar/database.py)**
   - Initialized the global SQLAlchemy database handler `db`.

4. **[models.py](file:///e:/promptwar/models.py)**
   - Created the core database models and relations:
     - `User`: Handles password hashing, role settings, and holds user data.
     - `UserPoints`: The ledger tracking points transactions dynamically to prevent manipulation.
     - `Blog`, `Comment`, `Like`: Community features supporting admin approval workflow.
     - `Article`, `ArticleRead`: Tracks reading progress and time elapsed.
     - `B2CResult`: Stores personal footprint calculations.
     - `B2BResult`: Stores Indian CCTS carbon intensity results.

5. **[auth.py](file:///e:/promptwar/auth.py)**
   - Configured `LoginManager` integration with Flask-Login.
   - Built REST endpoints for `/register`, `/login`, `/logout`, and `/me`.
   - Created the custom `@role_required` access control decorator.
   - Added `add_points_to_ledger` to safely credit points.

6. **[test_auth_and_db.py](file:///e:/promptwar/test_auth_and_db.py)**
   - Created an integration test suite validating all the schema definitions, auth routes, points ledger updates, and role protections on an in-memory SQLite database.

---

## Phase 2: Awareness Engine & Admin Verification Workflow

We have implemented the awareness engine reading tracker and the community blogging/admin moderation portal.

### Changes Made

1. **[routes.py](file:///e:/promptwar/routes.py)**
   - Implemented awareness article reading sessions (`start-read` and `complete-read`).
   - Implemented the 30-second time-interval check in `/api/articles/<id>/complete-read` to prevent gaming. Upon success, awards +10 points to the reader.
   - Implemented the blogging portal endpoints:
     - `POST /api/blogs`: Submits a draft (default status is `'pending'`).
     - `GET /api/blogs`: Public feed displaying only `'approved'` blogs.
     - `POST /api/blogs/<id>/comments`: Allows users to post comments and immediately earn +5 points.
     - `POST /api/blogs/<id>/like`: Toggles a like state on a blog post.
   - Implemented admin moderation:
     - `GET /api/admin/blogs/pending`: Retrieves pending blog posts (restricted to Admin role).
     - `POST /api/admin/blogs/<int:blog_id>/approve`: Approves and publishes the blog, and awards the author +100 points.
     - `POST /api/admin/blogs/<int:blog_id>/reject`: Rejects the draft.

2. **[test_phase2.py](file:///e:/promptwar/test_phase2.py)**
   - Created an integration test suite checking:
     - Blocked completions under 30 seconds.
     - Successful completions after 30 seconds (mocked/simulated time).
     - Hiding of pending blog posts from the public feed.
     - Admins approving blogs and authors gaining points.
     - Admins rejecting blogs.
     - Commenting and liking functionality.

---

## Phase 3: B2C & B2B Dual Carbon Calculators

We have implemented the B2C lifestyle calculator and the compliance-oriented B2B industrial calculator based on CCTS and India's sector mandates.

### Changes Made

1. **[routes.py](file:///e:/promptwar/routes.py)**
   - Implemented B2C lifestyle calculator at `POST /api/calculator/b2c`:
     - Multi-step calculations including Diet (red meat, dairy, local, imported), Transport (km driven for petrol/diesel, EV, public transit), and Energy (electricity consumption).
     - Awards +50 points to user points ledger.
   - Implemented B2B compliance-based industrial calculator at `POST /api/calculator/b2b`:
     - Scope 1 (boilers/combustion and direct process emissions) and Scope 2 (grid electricity emissions in tonnes) calculations.
     - Compares calculated emission intensity against mandated Indian sector caps (Steel: 2.1, Cement: 0.65, Power: 0.8, Other: 1.5).
     - Flags "Non-Compliant - Subject to NGT / CCTS Penalties" or calculates Carbon Credit Certificates (CCCs) earned.
     - Awards +50 points.
   - Implemented historical run tracker at `GET /api/calculator/history`.

2. **[test_phase3.py](file:///e:/promptwar/test_phase3.py)**
   - Created an integration test suite confirming:
     - Accurate B2C calculations (verifying exact arithmetic on dietary and travel metrics).
     - B2B compliant sector calculation, credit generation, and DB insertion.
     - B2B non-compliant sector calculation, cap verification, and penalty warning flags.
     - Calculation history endpoints loading correctly.

---

## Phase 4: Analytics, Visualizations & Tiered Mitigation

We have implemented backend visualization endpoints and a dynamic mitigation recommendation engine.

### Changes Made

1. **[routes.py](file:///e:/promptwar/routes.py)**
   - Implemented analytics endpoints:
     - `GET /api/analytics/b2c/<result_id>`: Formats lifestyle carbon footprint outputs with user actual values compared against global (2,000 kg) and national (1,900 kg) baselines. Outputs categorical breakdowns.
     - `GET /api/analytics/b2b/<result_id>`: Formats industrial footprint outputs including actual emission intensity versus cap and Scope 1 vs Scope 2 breakdown.
   - Implemented tiered mitigation recommendations:
     - `GET /api/calculator/b2c/<result_id>/mitigation`: Determines the user's highest emitting category and dynamically pulls matching Easy, Medium, and Hard actions.
     - `GET /api/calculator/b2b/<result_id>/mitigation`: Returns industrial energy audit and green fuels strategies.

2. **[test_phase4.py](file:///e:/promptwar/test_phase4.py)**
   - Created an integration test suite verifying:
     - B2C and B2B analytics endpoints return correct payloads.
     - Access controls block non-owners from viewing other users' calculations.
     - The mitigation engine dynamically detects the highest category and outputs corresponding Easy, Medium, and Hard solutions.

---

## Phase 5: High-End UI Design System (Enhanced Sea Green Theme)

We have built a responsive, dark-themed Single Page Application (SPA) dashboard showcasing beautiful glassmorphism structures, dynamic SVG biological animations, and Chart.js reporting. We also implemented custom visual selectors for the B2C calculator, a biological double-footprint background canvas, a live global points leaderboard, gamified animations, role-based point segregation, and dedicated industrial result components.

### Changes Made

1. **[app.py](file:///e:/promptwar/app.py)**
   - Initialized the main Flask server.
   - Wired database creation hooks and automatically seeds initial awareness articles and an admin user credentials `admin / Admin123!` to enable immediate, out-of-the-box system review.
   - Configured static folders path to host the single-page application index.
   
2. **[static/index.html](file:///e:/promptwar/static/index.html)**
   - Styled using custom CSS Grid responsive modules.
   - Embeds a stylized **double SVG carbon footprint outline** layered with organic biological gradients in the background (`.bg-neural-canvas`).
   - Added a full-screen **Gamified Tree Transition Overlay** (`#login-tree-overlay`) containing a stylized SVG tree, branches, and 15 interactive leaves.
   - Scaffolded the dedicated **Leaderboard Tab View** (`#view-leaderboard`) with a podium (Gold, Silver, Bronze levels) for the top 3 users, and a standard table below for ranks 4-10.
   - Redesigned the dashboard home view to make it more inspiring:
     - Welcoming greeting header with neon text-shine gradients.
     - Dynamic motivational quote block ("Daily Ecological Focus") with custom CSS accent borders.
     - Left: Circular footprint dial gauge display with a prominent "Start Assessment" prompt.
     - Right: Dynamic welcome cards. Prepares separate B2C panel (`#b2c-welcome-deck` for lifestyle resources) and B2B panel (`#b2b-welcome-deck` for regulatory BEE intensity caps and CCTS net-metering).
     - Removed the sidebar list widgets (global leaderboard card and assessment history logs card) to maximize screen space, making charts and mitigation advisory cards full-width.
   - Refactored the B2C calculator:
     - Step 1: Biological Sex (Female, Male selector cards), Body Composition (Normal, Underweight, Overweight, Obese cards), and Dietary Preference (Vegan, Vegetarian, Omnivore cards).
     - Step 2: Transit Mode (Walk/Bicycle, Public Transit, Private Vehicle cards), Fuel Type (Petrol, Diesel, Hybrid, LPG, Electric cards), and a custom Monthly Commuter range slider (defaulting to 2,000 km).
   - Added **Industrial Audit Results Modal** (`#b2b-result-modal`): Presents company audit parameters, compliant/non-compliant banners, Scope 1 & 2 carbon footprint tonnage, carbon credit trading certs, and easy/medium/hard industrial optimization pathways.
   
3. **[static/css/styles.css](file:///e:/promptwar/static/css/styles.css)**
   - Standardizes primary dark slate HSL color schemes.
   - Implements glassmorphism panels using properties like `backdrop-filter: blur(16px)` and micro-borders.
   - Customizes progress bars, slide animations, and custom scrollbars.
   - Styled the visual card selectors (`.selector-card`) with glassmorphic properties, glowing active borders (`border-color: var(--mint-green)`), and custom icon layouts.
   - Added circular gauge styles (`.gauge-dial-outer`, `.gauge-number`) and commute slider tracks.
   - Styled the **Login Tree Overlay** and SVG tree structure.
   - Added CSS keyframe animations for leaf wither (green to brown), leaf fall (gravity drop with rotation and sway), and floating $\text{CO}_2$ bubbles rising and fading.
   - Styled the dedicated Leaderboard podium (Gold, Silver, Bronze glow and distinct podium heights).
   - Styled the B2B results modal, compliance banners, and metric boxes.
   - Adjusted dashboard layout styles (`.dashboard-grid`) to span a single full-width column.
   
4. **[static/js/app.js](file:///e:/promptwar/static/js/app.js)**
   - Orchestrates REST calls to Python endpoints.
   - Handles the 30-second ticking progress bar countdown modal for articles.
   - Integrates Chart.js to render dual bar charts and categorical breakdown pie charts.
   - Intercepts successful login actions. Instead of directing the user straight to the dashboard, it triggers the tree leaf-fall animation loop, shedding leaves sequentially, floating glowing $\text{CO}_2$ symbols, updating status captions, and fading out the overlay after 4.5 seconds.
   - Added role checks in `onLoginSuccess()`: If the role is `industrial`, hides the points badge container and leaderboard tab, and opens the B2B welcome deck instead of the B2C deck.
   - Added navigation checks in `switchTab()`: Redirects non-common users away from the leaderboard tab back to the dashboard.
   - Updated B2B submission (`submitB2B()`): On completion, pops up the detailed compliance modal displaying emissions metrics, CCTS credits, and fetches/renders concrete easy, medium, and hard mitigation approaches.
   
5. **[auth.py](file:///e:/promptwar/auth.py)**
   - Updated `add_points_to_ledger()` to check the user's role. It returns `None` if the user's role is not `'common'`, preventing industrial owners and administrators from earning points or appearing on the leaderboard.
   
6. **[routes.py](file:///e:/promptwar/routes.py)**
   - Implemented `GET /api/leaderboard` route returning the top 10 registered user points totals.
   - Updated `POST /api/calculator/b2c` route to seamlessly support the new card-selector attributes (sex, body composition, dietary preference, transit mode, fuel type, monthly distance) while maintaining full backward-compatibility with legacy payload parameters (`red_meat`, `dairy`, etc.) to keep automated unit tests functioning correctly.

---

## Phase 5: Vertical Navigation, Logged Actions & Gemini AI Coach

We converted the Single Page Application's layout into a responsive vertical navigation sidebar, implemented the personalized carbon-offsetting action logging points ledger, and connected the Gemini-based AI coach chatbot.

### Changes Made

1. **[config.py](file:///e:/promptwar/config.py)**
   - Configured `GEMINI_API_KEY` supporting environment variables and fallback keys.

2. **[routes.py](file:///e:/promptwar/routes.py)**
   - Created action logging endpoints: `POST /api/actions/log` and `GET /api/actions/stats`.
   - Created AI Coach endpoint `POST /api/ai/coach` with self-healing fallback logic that sequentially queries stable `v1` and beta `v1beta` endpoints for multiple Gemini flash and pro model variants. It programmatically caches the successful endpoint configuration to ensure optimal performance.
   - Blocked points addition for any industrial owner role.

3. **[static/index.html](file:///e:/promptwar/static/index.html)**
   - Restructured layout using `.app-layout` wrapper featuring left vertical sidebar and top bar header.
   - Built dual dashboard layouts separating B2C common users from industrial B2B users.
   - Added `#view-ai-coach` chat panels.

4. **[static/css/styles.css](file:///e:/promptwar/static/css/styles.css)**
   - Styled the responsive left navigation menu, sidebar initials avatar, search topbar, action deck grid, and AI coach chat bubbles.
   - Implemented `.actions-grid` flex container layout ensuring the personalized cards align horizontally side-by-side and wrap dynamically to multiple rows under smaller viewports.

5. **[static/js/app.js](file:///e:/promptwar/static/js/app.js)**
   - Wired `switchTab` sidebar routing, login/profile display settings, action offset triggers, and AI Coach API streaming.

---

## Verification

You can verify all backend phases locally by running their respective test suites:

```bash
# Verify Phase 1
python test_auth_and_db.py

# Verify Phase 2
python test_phase2.py

# Verify Phase 3
python test_phase3.py

# Verify Phase 4
python test_phase4.py
```

### Local Application Execution
You can start the complete application by running:
```bash
python app.py
```
And navigate to `http://localhost:5000` in your web browser. Use the pre-seeded credentials `admin` / `Admin123!` to inspect the admin portal or sign up with a new account.

---

## Design Polish & Single-Assessment Redirection Updates

We have completed the following design and routing enhancements:

1. **Professional Modern Typography**:
   - Replaced Outfit font with the sleek, clean, modern combination of **Plus Jakarta Sans** and **Inter** loaded from Google Fonts in [index.html](file:///e:/promptwar/static/index.html) and [styles.css](file:///e:/promptwar/static/css/styles.css).

2. **Monochrome Emojis & Glowing Green Hover Effects**:
   - Applied CSS filters to render all emojis as clean, colorless grayscale elements by default. Upon hovering or active focus, they smoothly transition to a glowing emerald green, eliminating colorful cartoon-like clutter.

3. **Futuristic Neural Network Background**:
   - Replaced the heavy SVG background layout with a lightweight `<canvas>` particle engine.
   - Nodes and lines dynamically interconnect and float, colored in sea green, emerald, teal, and blue on a pitch-black background.
   - Added interactive mouse-coordinates tracking to create a smooth, subtle parallax depth effect that moves on cursor movement.

4. **Personalized Actions Horizontal Layout**:
   - Closed the unclosed `.dashboard-hero-split` grid in [index.html](file:///e:/promptwar/static/index.html) and added display overrides in [styles.css](file:///e:/promptwar/static/css/styles.css) to force full-width containment, ensuring the actions grid aligns cleanly as horizontal cards wrapping based on screen width.

5. **Infinite Calculator Retakes & Stationary Dashboard Results**:
   - Reverted the previous redirection rules. Clicking the **Calculator** tab now displays the questionnaire forms (B2C/B2B depending on role) *every single time*, allowing users to take or retake assessments infinitely.
   - The results cards (including the interactive Chart.js graphs and recommendations engine panels) stay permanently on the Dashboard tab, displaying fresh data after each assessment.
   - The dashboard buttons and quick action items dynamically update to prompt the user to "Update Assessment" or "Retake Compliance Audit" when an assessment has already been logged.
   - Enhanced the background neural canvas network colors and shadow glow (`ctx.shadowBlur = 15`) to make the network nodes stand out with maximum brightness.

6. **Restoration of Login Tree transition Overlay Styles**:
   - Added all missing CSS classes, animations, and keyframes for the gamified tree overlay in [styles.css](file:///e:/promptwar/static/css/styles.css).
   - Fixed a critical HTML syntax bug in [index.html](file:///e:/promptwar/static/index.html) (closing `</div>` tags were missing for `#article-reader-modal` at line 922). This was causing the browser to parse `#login-tree-overlay` as a nested child of the hidden article reader, which blocked it from rendering.
   - This restores the full-viewport dark login screen where the tree sequentially sheds leaves (green-to-brown wither transition, gravity drop rotation) and spawns floating red CO2 badges before automatically redirecting the user to the Dashboard view.
