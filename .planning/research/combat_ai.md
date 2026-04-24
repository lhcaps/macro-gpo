# Combat AI Research - Zedsu v2

**Project:** GPO Battle Royale Automation
**Researched:** 2026-04-24
**Overall Confidence:** MEDIUM-HIGH

## Executive Summary

The current Zedsu architecture uses a linear loop with template matching for asset detection. The core problem: **no enemy awareness**. The bot punches blindly and moves randomly, treating combat as a confirmation-of-equip problem rather than a dynamic decision problem.

Research confirms this is solvable with screen-only input. The path forward requires:
1. **Pixel-based activity detection** (immediate, no ML required)
2. **Health bar analysis** (moderate complexity, high value)
3. **Optional YOLO integration** (future phase, significant improvement)
4. **Combat state machine** replacing linear loops

The key insight from ecosystem research: **frame differencing is your best friend for real-time combat detection**. Real enemies create visible pixel changes that template matching cannot capture.

---

## Enemy Detection Techniques

### 1. Frame Difference Detection (PRIMARY RECOMMENDATION)

**Concept:** Compare consecutive game frames to detect pixel-level changes. Moving enemies, attacks, and damage effects all create visible motion.

**Implementation for Zedsu:**

```python
import cv2
import numpy as np

class FrameDiffDetector:
    def __init__(self, threshold=0.15, min_changed_pixels=500):
        self.threshold = threshold      # % of pixels that must change
        self.min_changed_pixels = min_changed_pixels
        self.prev_frame = None
    
    def capture_region(self, region):
        """Capture a focused region, not full screen."""
        screenshot = pyautogui.screenshot(region=region)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    
    def detect_activity(self, current_frame):
        if self.prev_frame is None:
            self.prev_frame = current_frame
            return False
        
        # Calculate frame difference
        diff = cv2.absdiff(current_frame, self.prev_frame)
        changed_pixels = np.count_nonzero(diff > 15)  # Tolerance for noise
        total_pixels = diff.size
        
        change_ratio = changed_pixels / total_pixels
        self.prev_frame = current_frame
        
        # Combat produces rapid, distributed changes
        return change_ratio > self.threshold and changed_pixels > self.min_changed_pixels
```

**Why this works for GPO BR:**
- Enemy movement creates large pixel changes across the screen
- Combat (hits, blocks) produces visible screen effects
- Damage flashes create sudden color changes
- Much faster than template matching (10-30ms vs 100-500ms)

**ROI (Region of Interest) Strategy:**

```python
# Focus detection on likely enemy areas (not full screen)
ROI_WEAPONS = (left + int(w*0.35), top + int(h*0.3),  # Upper area where enemies appear
               left + int(w*0.9), top + int(h*0.95))    # Down to ground level
```

### 2. Health Bar Pixel Detection

**Concept:** Roblox GPO shows enemy health bars when you hit enemies. Red pixels indicate damage opportunity.

**Implementation:**

```python
def detect_enemy_damage(screen_crop):
    """
    Look for red health bar pixels in enemy-facing screen regions.
    GPO typically shows enemy HP bar when they're taking damage.
    """
    # Convert to HSV for better red detection
    hsv = cv2.cvtColor(screen_crop, cv2.COLOR_BGR2HSV)
    
    # Red in HSV (two ranges due to hue wrap)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = mask1 + mask2
    
    # Count red pixels
    red_pixel_count = np.count_nonzero(red_mask)
    
    # Apply noise reduction
    kernel = np.ones((3,3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    
    return red_pixel_count > 100  # Threshold tunable
```

**Target regions for health bar scanning:**
```python
ENEMY_HP_SCAN_REGIONS = [
    # Bottom center (common enemy HP bar position)
    (0.30, 0.70, 0.70, 0.95),
    # Right side (player list / combat indicators)
    (0.75, 0.50, 0.98, 0.90),
    # Full center area (active combat)
    (0.25, 0.40, 0.75, 0.85),
]
```

### 3. Color Histogram Comparison

**Concept:** Compare color distribution between "idle" baseline and current frame. Significant histogram shifts indicate activity.

```python
def detect_histogram_shift(baseline, current, threshold=0.3):
    """
    Compare color histograms. Large shifts indicate game state changes.
    Good for detecting: enemy spawn, zone damage, dramatic combat.
    """
    baseline_hist = cv2.calcHist([baseline], [0], None, [256], [0, 256])
    current_hist = cv2.calcHist([current], [0], None, [256], [0, 256])
    
    # Normalize
    cv2.normalize(baseline_hist, baseline_hist, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(current_hist, current_hist, 0, 1, cv2.NORM_MINMAX)
    
    # Compare using correlation
    similarity = cv2.compareHist(baseline_hist, current_hist, cv2.HISTCMP_CORREL)
    
    return similarity < (1.0 - threshold)
```

### 4. Character Model Color Detection

**Concept:** Roblox characters have distinctive colors. Scan for "non-background" color clusters.

```python
def detect_player_colors(screen_region, background_sample):
    """
    Look for pixels that don't match the expected background.
    Returns (detected: bool, center: tuple)
    """
    hsv = cv2.cvtColor(screen_region, cv2.COLOR_BGR2HSY)
    
    # Known player skin/outfit color ranges (tunable after capture)
    # This requires calibration against actual GPO character colors
    player_hues = [
        (0, 25),    # Skin tones
        (35, 65),   # Green/outfit
        (100, 130), # Blue/outfit
        (170, 180), # Red/outfit
    ]
    
    player_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in player_hues:
        mask = cv2.inRange(hsv[:,:,0], low, high)
        player_mask = cv2.bitwise_or(player_mask, mask)
    
    # Find largest contour (likely a character)
    contours, _ = cv2.findContours(player_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > 500:  # Min size threshold
            M = cv2.moments(largest)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                return True, (cx, cy)
    
    return False, None
```

### 5. Template Matching Enhancement (IRUS Reference Pattern)

From IRUS Neural combat analysis, the "Gate System" approach:

```python
class GateCombatDetector:
    """
    Three-phase detection inspired by IRUS shake detection:
    - Gate 1: WAIT for combat indicator
    - Gate 2: TRACK the indicator movement  
    - Gate 3: REACT when threshold crossed
    """
    
    GATE1_STABLE_FRAMES = 3      # Must see indicator for N frames
    GATE2_MOVEMENT_THRESH = 15  # Pixels of movement
    GATE3_DETECTION_THRESH = 8   # Frame diff threshold
    
    def __init__(self):
        self.state = "GATE1"
        self.consecutive_detections = 0
        self.last_position = None
        self.last_frame = None
    
    def process_frame(self, current_frame):
        if self.state == "GATE1":
            # Look for combat indicators
            if self._has_combat_indicator(current_frame):
                self.consecutive_detections += 1
                if self.consecutive_detections >= self.GATE1_STABLE_FRAMES:
                    self.state = "GATE2"
                    self.last_position = self._get_indicator_position(current_frame)
            else:
                self.consecutive_detections = 0
                
        elif self.state == "GATE2":
            # Track if indicator is moving (enemies nearby)
            current_pos = self._get_indicator_position(current_frame)
            if current_pos and self.last_position:
                movement = abs(current_pos[0] - self.last_position[0]) + \
                          abs(current_pos[1] - self.last_position[1])
                if movement > self.GATE2_MOVEMENT_THRESH:
                    self.state = "GATE3"
            self.last_position = current_pos
            
        elif self.state == "GATE3":
            # Frame diff confirms combat
            if self.last_frame is not None:
                diff = cv2.absdiff(current_frame, self.last_frame)
                changed = np.count_nonzero(diff > self.GATE3_DETECTION_THRESH)
                if changed > 800:  # Significant activity
                    return "COMBAT_ACTIVE"
            self.last_frame = current_frame
            
        self.last_frame = current_frame
        return self.state
```

---

## Combat State Machine Design

### Recommended State Machine Architecture

Replace the current linear `auto_punch()` loop with a proper FSM:

```
┌─────────────┐
│   LOBBY     │──► Queue & Wait
└─────────────┘
       │
       ▼
┌─────────────┐
│ WAIT_MATCH  │──► Match starts
└─────────────┘
       │
       ▼
┌─────────────┐
│  IN_COMBAT  │◄──────────────┐
│  ├─ IDLE    │               │
│  ├─ SEARCH  │               │
│  ├─ ENGAGE  │               │
│  ├─ RETREAT │               │
│  └─ SPRINT  │               │
└─────────────┘               │
       │                      │
       ├──────► SPECTATING ───┘
       │                      │
       ▼                      │
┌─────────────┐               │
│ POST_MATCH  │───────────────┘
└─────────────┘
       │
       ▼
    (restart)
```

### State Definitions

```python
class CombatState(Enum):
    LOBBY = "lobby"
    QUEUE = "queue"
    WAIT_MATCH = "wait_match"
    
    # Combat substates
    COMBAT_IDLE = "combat_idle"      # No enemies detected
    COMBAT_SEARCH = "combat_search"   # Looking for enemies
    COMBAT_ENGAGE = "combat_engage"  # Enemy detected, attacking
    COMBAT_RETREAT = "combat_retreat"# Low HP, evading
    COMBAT_SPRINT = "combat_sprint"  # Moving to zone/loot
    
    SPECTATING = "spectating"
    POST_MATCH = "post_match"
```

### Combat State Transition Logic

```python
class CombatStateMachine:
    def __init__(self, engine):
        self.state = CombatState.WAIT_MATCH
        self.substate = None
        self.engine = engine
        self.state_time = time.time()
        
        # Perception layer
        self.enemy_detector = FrameDiffDetector()
        self.hp_detector = HealthBarDetector()
        self.activity_tracker = ActivityTracker()
    
    def update(self):
        """Called each loop iteration. Returns action to take."""
        elapsed = time.time() - self.state_time
        
        # Global transitions
        if self._check_spectating():
            return self._transition(CombatState.SPECTATING)
        if self._check_post_match():
            return self._transition(CombatState.POST_MATCH)
        
        # State-specific logic
        if self.state == CombatState.WAIT_MATCH:
            return self._handle_wait_match()
            
        elif self.state == CombatState.COMBAT_IDLE:
            return self._handle_idle()
            
        elif self.state == CombatState.COMBAT_SEARCH:
            return self._handle_search()
            
        elif self.state == CombatState.COMBAT_ENGAGE:
            return self._handle_engage()
            
        elif self.state == CombatState.COMBAT_RETREAT:
            return self._handle_retreat()
            
        elif self.state == CombatState.COMBAT_SPRINT:
            return self._handle_sprint()
    
    def _handle_idle(self):
        """No enemies detected. Roam or wait."""
        frame = self.engine.capture_game_frame()
        
        # Check for any activity
        if self.enemy_detector.detect_activity(frame):
            return self._transition(CombatState.COMBAT_SEARCH, action="enemy_spotted")
        
        # Periodic movement toward zone center
        if random.random() < 0.3:
            return Action(MOVE_FORWARD, duration=0.5)
        
        return Action(STANDBY, duration=0.3)
    
    def _handle_search(self):
        """Enemy likely nearby. Turn toward and locate."""
        frame = self.engine.capture_game_frame()
        
        # Aggressive frame diff check
        if self.enemy_detector.detect_activity(frame):
            self.state_time = time.time()  # Refresh
            
            # Check HP status
            if self.hp_detector.my_health_low(frame):
                return self._transition(CombatState.COMBAT_RETREAT)
            
            return Action(TURN_TOWARD_MOVEMENT, continue_state=CombatState.COMBAT_SEARCH)
        
        # Timeout: go back to idle
        if time.time() - self.state_time > 5:
            return self._transition(CombatState.COMBAT_IDLE)
        
        return Action(STANDBY, duration=0.2)
    
    def _handle_engage(self):
        """Confirmed enemy. Full combat mode."""
        frame = self.engine.capture_game_frame()
        
        # HP check
        if self.hp_detector.my_health_low(frame):
            return self._transition(CombatState.COMBAT_RETREAT)
        
        # Punch pattern
        for _ in range(5):
            self.engine.punch()
        
        # Movement after burst
        return Action(DODGE_MOVE, next_state=CombatState.COMBAT_ENGAGE)
    
    def _handle_retreat(self):
        """Low HP. Run away, wait for recovery."""
        frame = self.engine.capture_game_frame()
        
        # Move backward
        if not self.hp_detector.my_health_critical(frame):
            return self._transition(CombatState.COMBAT_IDLE)
        
        return Action(MOVE_BACKWARD, duration=1.0)
```

### Health-Based Fight-or-Flight Logic

```python
class HealthDecisionEngine:
    """Implements fight-or-flight based on HP percentage."""
    
    CRITICAL_THRESHOLD = 0.15   # 15% HP - must retreat
    LOW_THRESHOLD = 0.35        # 35% HP - consider retreat
    HEALTHY_THRESHOLD = 0.60    # 60% HP - safe to engage
    
    def __init__(self, config):
        self.hp_history = deque(maxlen=10)  # Track over time
        
    def analyze(self, frame):
        """Returns combat recommendation based on HP."""
        current_hp = self._detect_my_hp(frame)
        self.hp_history.append(current_hp)
        
        # Calculate trend
        if len(self.hp_history) >= 3:
            hp_trend = self.hp_history[-1] - self.hp_history[0]
            taking_damage = hp_trend < -0.1
        else:
            taking_damage = False
        
        # Decision matrix
        if current_hp < self.CRITICAL_THRESHOLD:
            return "RETREAT", "Critical HP"
        elif current_hp < self.LOW_THRESHOLD:
            if taking_damage:
                return "RETREAT", "Low HP, taking damage"
            else:
                return "CAUTION", "Low HP, but stable"
        elif current_hp > self.HEALTHY_THRESHOLD and not taking_damage:
            return "ENGAGE", "Full HP, enemy nearby"
        
        return "TRADE", "Normal HP, active combat"
    
    def _detect_my_hp(self, frame):
        """Extract my health bar percentage."""
        # GPO HP bar location - configurable
        hp_region = self._extract_hp_region(frame)
        
        # Count non-white pixels in HP bar (white = lost HP)
        gray = cv2.cvtColor(hp_region, cv2.COLOR_BGR2GRAY)
        _, hp_bar = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        total_pixels = hp_bar.size
        hp_pixels = np.count_nonzero(hp_bar)
        
        return hp_pixels / total_pixels if total_pixels > 0 else 1.0
```

---

## BR-Specific AI Logic

### Zone Awareness

```python
class ZoneAwareness:
    """
    GPO BR zone mechanics - no explicit UI in many versions.
    Fallback to: time-based zone estimation + movement toward center.
    """
    
    def __init__(self):
        self.match_start_time = None
        self.zone_center = None  # (x, y) in relative coords
        self.safe_zone_radius = 0.3  # Relative to map
        
    def on_match_start(self):
        self.match_start_time = time.time()
        self.zone_center = (0.5, 0.5)  # Assume center initially
        
    def should_move_to_zone(self, player_position):
        """Return True if player should move toward safe zone."""
        if not self.match_start_time:
            return False
            
        elapsed = time.time() - self.match_start_time
        
        # GPO BR zones shrink over time
        # Rough timeline (tunable):
        # 0-60s: No zone pressure
        # 60-120s: First shrink warning
        # 120-180s: Zone closing
        
        if elapsed < 60:
            return False
        elif elapsed < 120:
            # First phase - zone closing, prioritize center
            return self._distance_to_center(player_position) > 0.4
        else:
            # Active zone - always favor center
            return self._distance_to_center(player_position) > 0.2
    
    def get_movement_direction(self, player_position):
        """Return direction vector toward safe zone center."""
        dx = self.zone_center[0] - player_position[0]
        dy = self.zone_center[1] - player_position[1]
        norm = math.sqrt(dx*dx + dy*dy)
        if norm < 0.01:
            return (0, 0)
        return (dx/norm, dy/norm)  # Normalized
```

### Roaming Intelligence

```python
class RoamingStrategy:
    """
    Replace random movement with smart roaming decisions.
    """
    
    def __init__(self):
        self.last_activity_time = time.time()
        self.roam_target = None
        self.roam_duration = 0
        
    def decide_next_move(self, enemy_detected, time_since_activity):
        """
        Returns (move_key, duration) tuple.
        """
        # High activity - nearby enemy likely
        if time_since_activity < 2:
            return (None, 0)  # Stand still, let enemy come
        
        # No activity for a while - search mode
        if time_since_activity > 8:
            # Pick a random direction and move toward it
            self.roam_target = random.choice(['w', 'a', 's', 'd'])
            self.roam_duration = random.uniform(0.5, 1.5)
            return (self.roam_target, self.roam_duration)
        
        # Moderate activity - patrol around current area
        if random.random() < 0.6:
            keys = ['a', 'd']  # Strafe left/right
            return (random.choice(keys), random.uniform(0.2, 0.5))
        
        return (None, 0)
```

### KDA Tracking

```python
class KDATracker:
    """
    Track eliminations during the match.
    """
    
    def __init__(self):
        self.kills = 0
        self.deaths = 0
        self.assists = 0
        self.elimination_timestamps = []
        
    def on_enemy_killed(self):
        """Call when we detect an enemy elimination."""
        self.kills += 1
        self.elimination_timestamps.append(time.time())
        
    def on_death(self):
        """Call when we enter spectating."""
        self.deaths += 1
        
    def get_recent_kills(self, window_seconds=60):
        """Kills in the last N seconds - useful for hot streak detection."""
        cutoff = time.time() - window_seconds
        return sum(1 for ts in self.elimination_timestamps if ts > cutoff)
        
    def is_on_streak(self, threshold=2, window=30):
        """Returns True if on a killing streak."""
        return self.get_recent_kills(window) >= threshold
```

---

## Practical Implementation Recommendations

### Phase 1: Minimal Viable Enemy Detection (1-2 days)

**Goal:** Detect "something is happening" without identifying what.

**Implementation:**
```python
class MinimalEnemyDetector:
    """
    Lightweight frame differencing for activity detection.
    No ML, no training required. 15-30ms per check.
    """
    
    def __init__(self):
        self.prev_frame = None
        self.threshold_pixels = 800
        self.threshold_ratio = 0.008
        
    def check(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return False
            
        diff = cv2.absdiff(gray, self.prev_frame)
        changed = np.count_nonzero(diff > 20)
        ratio = changed / diff.size
        
        self.prev_frame = gray
        
        return changed > self.threshold_pixels and ratio > self.threshold_ratio
```

**Integration with current code:**
```python
# In bot_engine.py, modify auto_punch() loop:
while self.is_running():
    frame = self.capture_game_frame()
    
    if self.activity_detector.check(frame):
        self.log("Activity detected - enemy likely nearby")
        # Enter search/engage mode instead of blind punching
    
    # Existing combat logic continues...
```

### Phase 2: Health Bar Integration (2-3 days)

**Goal:** Know when we're winning vs losing.

**Implementation:** Add `HealthBarDetector` class with:
- `detect_my_hp()` - Parse our HP bar
- `detect_enemy_hp()` - Look for enemy damage indicators
- `is_taking_damage()` - Track HP trend

**ROI Strategy:** Only scan bottom 30% of screen where HP bars typically appear.

### Phase 3: Combat State Machine (3-5 days)

**Goal:** Replace linear `auto_punch()` with intelligent FSM.

**Migration Path:**
1. Create `CombatStateMachine` class alongside existing code
2. Add state detection methods
3. Gradually route decisions through new system
4. Remove old linear loop once new system is stable

### Phase 4: Optional YOLO Enhancement (Future)

**When to consider:** If Phases 1-3 still have >30% false positives.

**Recommended approach:**
- Use YOLOv11n (6MB nano model, 3.3ms inference on GPU)
- Train on GPO character screenshots
- Classes: `player`, `enemy`, `chest`, `weapon`

**CPU fallback:** If no GPU, stick with pixel methods. YOLO on CPU is 10-50x slower.

---

## Migration from Current Architecture

### Current Flow (Linear)
```
Lobby → Queue → Wait → [MELee LOOP: equip → 5 punches → move → repeat] → Post
```

### Target Flow (State Machine)
```
Lobby → Queue → Wait → 
  COMBAT_IDLE: wait + roam
    ↓ activity detected
  COMBAT_SEARCH: scan + turn
    ↓ enemy confirmed
  COMBAT_ENGAGE: punch + dodge
    ↓ HP low
  COMBAT_RETREAT: run + wait
    ↓ enemy gone
  COMBAT_IDLE: (loop)
    ↓ died
  SPECTATING: wait for respawn
    ↓ match end
  POST_MATCH
```

### Incremental Migration Strategy

**Step 1:** Add detection layer (no behavior change)
```python
# Add to BotEngine.__init__
self.activity_detector = MinimalEnemyDetector()
self.combat_state = "blind_punch"  # Legacy mode
```

**Step 2:** Wrap existing loop with state detection
```python
def auto_punch(self):
    # Existing setup code...
    
    while self.is_running():
        # NEW: Detect combat context
        frame = self.capture_game_frame()
        is_active = self.activity_detector.check(frame)
        
        if is_active:
            self.log("Enemy activity detected!")
        
        # EXISTING: Blind punch loop continues
        # (gradually replace with state-based decisions)
```

**Step 3:** Replace specific behaviors one at a time
- Replace random movement with `RoamingStrategy`
- Replace blind punching with engagement check
- Add HP-based retreat

**Step 4:** Full FSM (optional, when Phase 3 complete)

---

## Key Risks

### Risk 1: Detection False Positives
**Problem:** Frame diff detects camera movement, not enemies.
**Mitigation:**
- Combine with HP bar analysis (both must agree)
- Add minimum duration requirement (enemy must appear for 3+ frames)
- Filter out edge-of-screen movement (likely camera)

### Risk 2: Performance Impact
**Problem:** OpenCV processing adds latency to main loop.
**Mitigation:**
- Use ROI (Region of Interest) instead of full screen
- Cache previous frame, reuse for multiple checks
- Throttle detection to every 100-200ms, not every frame
- Profile on target hardware before optimization

### Risk 3: GPO Updates Break Detection
**Problem:** Game updates change UI, health bar colors, etc.
**Mitigation:**
- Use relative coordinates (percentages of screen) not absolute
- Make thresholds configurable via `config.py`
- Add "calibration mode" for users to re-tune after updates
- Template matching still works for UI; add pixel analysis as supplementary

### Risk 4: Over-Complicated State Machine
**Problem:** FSM with too many states becomes undebuggable.
**Mitigation:**
- Start with 3 states: IDLE, ENGAGE, RETREAT
- Add states only when clear improvement
- Log all state transitions for debugging
- Keep transitions simple: "if X then Y"

### Risk 5: Anti-Cheat Detection
**Problem:** Deterministic bot behavior is detectable.
**Mitigation:**
- Use `controller.py` human-like input (already done)
- Randomize timing within ranges, not fixed intervals
- Add "jitter" to movement patterns
- Don't be perfect - occasional missed detections are fine

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Risk | Priority |
|---------|--------|--------|------|----------|
| Frame diff detection | HIGH | LOW | LOW | **P1** |
| HP bar parsing | HIGH | MEDIUM | MEDIUM | **P2** |
| State machine (3 states) | HIGH | MEDIUM | LOW | **P3** |
| Smart roaming | MEDIUM | LOW | LOW | **P3** |
| Enemy streak tracking | LOW | LOW | LOW | P4 |
| YOLO detection | HIGH | HIGH | MEDIUM | Future |
| Zone awareness | MEDIUM | MEDIUM | MEDIUM | Future |

---

## Sources

- [1] SEIA Framework - State-Based Image Automation (GitHub)
- [2] YOLOv11n for CS2 - Real-Time Player Detection (AI Base)
- [3] Game AI Behavior Trees - UnityQueen 2026
- [4] Combat State Management - Oreate AI Blog
- [5] Frame Difference Detection - Stack Overflow / Gist
- [6] Health Bar Detection with OpenCV - Sahcim/HealthBarDetector
- [7] RL-Agent for Roblox - YOLOv11 + RF-DETR PvP Combat
- [8] Real-Time YOLO Optimization - Medium/Gautamashastry 2026
