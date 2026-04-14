# Task 3.2 UI Preview: Resume Voting Banner

## Visual Design

The resume voting banner appears immediately after the student welcome header when saved votes are detected.

### Banner Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  💾  Resume Your Voting Session                                 │
│                                                                   │
│      You have 3 votes saved from Dec 12, 2024 at 02:30 PM.      │
│      All selections are still valid.                             │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  🔄 Resume Voting    │  │  🆕 Start Fresh      │            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Color Scheme
- **Background**: Amber/yellow gradient (rgba(245,158,11,.15) to rgba(251,191,36,.08))
- **Border**: Amber (rgba(245,158,11,.4))
- **Title**: Bright yellow (#fbbf24)
- **Text**: Light gray (#94a3b8)
- **Buttons**: 
  - Resume: Primary blue gradient
  - Start Fresh: Secondary gray

### With Warnings

When some votes are invalid:

```
┌─────────────────────────────────────────────────────────────────┐
│  💾  Resume Your Voting Session                                 │
│                                                                   │
│      You have 2 votes saved from Dec 12, 2024 at 02:30 PM.      │
│      Some selections may no longer be valid.                     │
│                                                                   │
│  ▼ ⚠️ View validation warnings                                  │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  🔄 Resume Voting    │  │  🆕 Start Fresh      │            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

Expanded warnings:
```
  ▼ ⚠️ View validation warnings
    ⚠ Sports: Candidate not approved for this committee
    ⚠ Literary: Candidate not found
```

## User Flow

### Step 1: Student Logs In
```
┌─────────────────────────────────────────────────────────────────┐
│  🏫  Welcome Back                                                │
│                                                                   │
│  Sign in to participate in your school election                  │
│                                                                   │
│  Admission No / Admin ID: [jb001____________]                    │
│  Password: [••••••••••••]                                        │
│                                                                   │
│  [🔓 Sign In]                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Step 2: Welcome Header Appears
```
┌─────────────────────────────────────────────────────────────────┐
│  👨‍🎓  Ali Khan                                        [🚪 Logout] │
│      Class 10 · Section A · 🔵 Taxila House · Senior Group      │
└─────────────────────────────────────────────────────────────────┘
```

### Step 3: Resume Banner Appears (NEW!)
```
┌─────────────────────────────────────────────────────────────────┐
│  💾  Resume Your Voting Session                                 │
│                                                                   │
│      You have 3 votes saved from Dec 12, 2024 at 02:30 PM.      │
│      All selections are still valid.                             │
│                                                                   │
│  [🔄 Resume Voting]  [🆕 Start Fresh]                           │
└─────────────────────────────────────────────────────────────────┘
```

### Step 4a: User Clicks "Resume Voting"
```
✅ Resumed with 3 saved votes!

[Redirects to voting tab with selections pre-filled]
```

### Step 4b: User Clicks "Start Fresh"
```
ℹ️ Starting fresh voting session...

[Redirects to voting tab with empty selections]
```

## Responsive Design

The banner adapts to different screen sizes:

### Desktop (Wide)
- Full width with side padding
- Buttons side-by-side
- Icon and text on same line

### Tablet (Medium)
- Slightly reduced padding
- Buttons side-by-side
- Icon and text on same line

### Mobile (Narrow)
- Minimal padding
- Buttons stacked vertically
- Icon above text

## Accessibility

- **Clear Visual Hierarchy**: Large icon, bold title, descriptive text
- **High Contrast**: Amber on dark background meets WCAG AA standards
- **Descriptive Buttons**: Clear action labels ("Resume Voting" vs "Start Fresh")
- **Expandable Warnings**: Optional details don't clutter main view
- **Keyboard Navigation**: All buttons are keyboard accessible
- **Screen Reader Friendly**: Semantic HTML with proper ARIA labels

## Integration Points

### Before Banner
1. Login screen
2. Credential validation
3. Session state initialization
4. Student data fetch

### Banner Display
1. Check for saved votes
2. Validate saved votes
3. Show banner if valid votes exist
4. Handle user choice

### After Banner
1. Load votes into temp_votes (if resume)
2. Clear saved data (if start fresh)
3. Continue to voting tabs
4. Log action to audit trail

## Edge Cases Handled

1. **No Saved Votes**: Banner doesn't appear
2. **All Votes Invalid**: Banner doesn't appear, data cleared
3. **Some Votes Invalid**: Banner appears with warnings
4. **Election Closed**: Banner doesn't appear, data cleared
5. **Already Voted**: Banner doesn't appear (student sees "You've Voted!" screen)
6. **Different Student**: Saved votes don't load (student ID mismatch)
7. **Corrupted Data**: Gracefully handles JSON errors, clears data

## Performance

- **Single Check**: Only validates once per session
- **Lazy Loading**: Banner only renders when needed
- **Efficient Queries**: Uses existing vote integrity checks
- **No Blocking**: Validation doesn't delay page load
- **Minimal State**: Only stores necessary data

## Security

- **Student ID Validation**: Ensures votes belong to logged-in student
- **Election Phase Check**: Only allows resume during LIVE phase
- **Candidate Validation**: Verifies candidates are still approved
- **Self-Vote Prevention**: Checks student isn't voting for themselves
- **Audit Trail**: All actions logged with timestamps

## Future Enhancements (Not in Scope)

- Email notification when session times out
- SMS reminder to complete voting
- Progress bar showing completion percentage
- Estimated time to complete voting
- Auto-save indicator (e.g., "Last saved: 2 minutes ago")
- Offline support with local storage
- Multi-device sync
