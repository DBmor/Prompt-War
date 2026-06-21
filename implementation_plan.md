# Implementation Plan - Infinite Retakes and Brighter Neural Background

This plan updates the front-end to allow infinite calculator retakes (rendering the questionnaire form every time) and to make the background network dots brighter and more glowing.

## User Review Required

> [!NOTE]
> The single-assessment block and redirection logic is completely removed. Users can now retake/update the carbon calculator infinitely. The carbon charts and mitigation recommendations will remain permanently in their dashboard placeholders, showing fresh data after every successful submission.

## Proposed Changes

### Front-End Routing & Interaction

#### [MODIFY] [app.js](file:///e:/promptwar/static/js/app.js)
- **Neural Network Brightness**:
  - Increase particle color alpha transparency to values between `0.85` and `0.95` with more vibrant color codes.
  - Increase shadow glow blur (`ctx.shadowBlur`) from `8` to `15` to render significantly brighter nodes.
  - Increase connection line alpha to make the mesh structure more distinct.
- **Simplification of checkCalculatorStatusAndRender**:
  - Remove all redirect and DOM element-shifting logic (no longer appends dashboard items to calculator results container).
  - Simply toggle the B2C or B2B calculator wrapper visibility based on the logged-in user's role.
  - Hide the results container (`#calc-results-container`) completely since results are now viewed directly on the dashboard.
- **Remove returnElementsToDashboard**:
  - Delete `returnElementsToDashboard()` entirely since dashboard card placement remains stationary.
- **Update switchTab Navigation**:
  - Remove invocation of `returnElementsToDashboard()`.
- **Align Dashboard Button Label Triggers**:
  - Update `loadDashboardData()` button labels to use "Retake Assessment" and "Update Assessment" instead of redirecting the user to static results, confirming they can click the buttons to re-submit parameters at any time.

#### [MODIFY] [styles.css](file:///e:/promptwar/static/css/styles.css)
- **Restore Tree Transition Animations & Overlays**:
  - Add `.tree-overlay` rules to position the animation canvas full-viewport with dark background.
  - Add `.tree-transition-card` and `.tree-container` rules to center the tree SVG and establish a glowing organic perimeter.
  - Add `.transition-leaf`, `.wither` and `.fall` transition properties to control the color fade (green to brown) and gravitational dropdown rotation.
  - Add `.co2-bubble` and `@keyframes float-co2` rules to manage the floating text tags spawn sequence.

## Verification Plan

### Manual Verification
1. **Bright Background Network**:
   - Verify that neural canvas network dots appear significantly brighter and cast a stronger glow.
2. **Infinite Calculator Retakes**:
   - Log in as a common user. Click the **Calculator** tab. Verify the questionnaire form displays immediately.
   - Fill out the form and submit. Verify redirect to the Dashboard shows updated metric values and analytics charts.
   - Click the **Calculator** tab again. Verify the questionnaire form displays successfully once more instead of showing a blank page or a completed screen.
   - Repeat the process for an Industrial user.
3. **Login Tree Transition**:
   - Log out, then log in again.
   - Confirm the full-screen Tree Transition Overlay displays, showing the green leaf shedding sequence, status updates, and floating CO2 badges.
   - Verify that once all leaves are shed, the screen redirects automatically to the Dashboard.
