# Calendar Grid Integration Guide

## Overview

The enhanced ScheduleGrid component provides a dynamic, interactive calendar view that automatically updates when the AI generates schedules. This document explains how the calendar grid works and how to integrate it with AI responses.

## Architecture

```
AI Response → useScheduleGrid Hook → ScheduleGrid Component → Visual Calendar
```

### Components

1. **ScheduleGrid Component** (`src/components/schedule/ScheduleGrid.tsx`)
   - Renders the visual calendar grid
   - Displays courses in correct time slots
   - Shows conflict indicators
   - Supports click handlers

2. **useScheduleGrid Hook** (`src/hooks/useScheduleGrid.ts`)
   - Manages schedule state
   - Handles AI response parsing
   - Detects conflicts automatically
   - Provides update methods

## Features

### 1. Dynamic Time Slot Rendering

The grid displays time slots from 8:00 AM to 8:00 PM with 80px per hour:

```typescript
const TIME_SLOTS = [
  '8:00', '9:00', '10:00', '11:00', '12:00',
  '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'
];
```

### 2. Day Parsing

Supports various day format abbreviations:
- `M` → Monday
- `T` → Tuesday  
- `W` → Wednesday
- `Th` → Thursday
- `F` → Friday
- `TTh` → Tuesday and Thursday
- `MWF` → Monday, Wednesday, Friday

### 3. Time Format Support

Handles both 12-hour and 24-hour time formats:
- `"10:00 AM"` → Parsed correctly
- `"10:00"` → Treated as 24-hour format
- `"14:00"` → Converted to 2:00 PM for display

### 4. Color Coding

Automatically assigns distinct colors to each course:

```typescript
const COLOR_PALETTE = [
  'bg-blue-500',
  'bg-purple-500',
  'bg-green-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-teal-500',
  'bg-red-500',
];
```

### 5. Conflict Detection

Automatically detects and highlights schedule conflicts:
- Red ring around conflicting courses
- Alert icon in top-right corner
- Conflict count in header
- Detailed conflict alert below grid

### 6. Smooth Transitions

All updates include smooth CSS transitions:
- 300ms ease-in-out transitions
- Fade-in animations for new courses
- Scale effect on hover (when editable)

## Usage

### Basic Usage

```typescript
import ScheduleGrid from "@/components/schedule/ScheduleGrid";
import { useScheduleGrid } from "@/hooks/useScheduleGrid";

function MySchedulePage() {
  const { sections, conflicts } = useScheduleGrid();
  
  return (
    <ScheduleGrid 
      sections={sections}
      conflicts={conflicts}
      editable={true}
    />
  );
}
```

### With AI Integration

```typescript
import { useScheduleGrid } from "@/hooks/useScheduleGrid";

function AIScheduleBuilder() {
  const { sections, conflicts, updateFromAI } = useScheduleGrid();
  
  const handleAIResponse = async (aiResponse: any) => {
    // Automatically parses and updates the calendar
    await updateFromAI(aiResponse);
  };
  
  return (
    <div>
      <ScheduleGrid sections={sections} conflicts={conflicts} />
      <button onClick={() => handleAIResponse(aiScheduleData)}>
        Apply AI Schedule
      </button>
    </div>
  );
}
```

### Manual Section Management

```typescript
const { 
  sections, 
  addSection, 
  removeSection, 
  clearSections 
} = useScheduleGrid();

// Add a section
await addSection({
  id: "section-1",
  course_id: "course-1",
  section_number: "CSC 101",
  professor_name: "Dr. Johnson",
  days: "MWF",
  start_time: "10:00",
  end_time: "11:00",
  location: "NAC 5/150",
  modality: "In-person",
  enrolled: 25,
  capacity: 30,
  scraped_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});

// Remove a section
await removeSection("section-1");

// Clear all sections
clearSections();
```

## AI Response Format

The `updateFromAI` method supports multiple response formats:

### Format 1: Direct Array

```json
[
  {
    "id": "section-1",
    "section_number": "CSC 101",
    "days": "MWF",
    "start_time": "10:00",
    "end_time": "11:00",
    ...
  }
]
```

### Format 2: Sections Object

```json
{
  "sections": [
    {
      "id": "section-1",
      "section_number": "CSC 101",
      ...
    }
  ]
}
```

### Format 3: Courses with Sections

```json
{
  "courses": [
    {
      "course_code": "CSC 101",
      "sections": [
        {
          "id": "section-1",
          "days": "MWF",
          ...
        }
      ]
    }
  ]
}
```

### Format 4: Nested Schedule

```json
{
  "schedule": {
    "sections": [...]
  }
}
```

## Grid Position Calculation

The grid uses precise calculations to position courses:

```typescript
// Each hour = 80px
// Base time = 8:00 AM

const startMinutes = timeToMinutes("10:00"); // 600 minutes
const baseMinutes = timeToMinutes("8:00");   // 480 minutes

const top = ((startMinutes - baseMinutes) / 60) * 80;
// top = ((600 - 480) / 60) * 80 = 160px

const endMinutes = timeToMinutes("11:00");   // 660 minutes
const height = ((endMinutes - startMinutes) / 60) * 80;
// height = ((660 - 600) / 60) * 80 = 80px
```

## Responsive Behavior

The grid adapts to different screen sizes:
- Minimum width: 800px
- Horizontal scroll on smaller screens
- Touch-friendly on mobile devices
- Maintains aspect ratio

## Conflict Detection Algorithm

Conflicts are detected by:

1. Checking if courses share common days
2. Comparing time ranges for overlaps
3. Flagging sections with overlapping times

```typescript
// Two courses conflict if:
// 1. They share at least one day
// 2. Their times overlap

const hasCommonDay = days1.some(day => days2.includes(day));
const timesOverlap = (start1 < end2 && end1 > start2);

if (hasCommonDay && timesOverlap) {
  // Conflict detected!
}
```

## Performance Considerations

### Memoization

The component uses `useMemo` to optimize:
- Event processing
- Unique course calculation
- Day-based filtering

### Transition Delays

Updates include 300ms delays to allow smooth animations:

```typescript
setTimeout(() => setIsUpdating(false), 300);
```

### Conflict Checking

Conflicts are checked asynchronously to avoid blocking the UI:

```typescript
const updateConflicts = useCallback(async (newSections) => {
  // Async conflict detection
  const conflicts = await checkScheduleConflicts(sectionIds);
  setConflicts(conflicts);
}, []);
```

## Styling

### Course Block Styling

```css
/* Base course block */
.course-block {
  @apply text-white p-2 rounded shadow-md;
  transition: all 300ms ease-in-out;
}

/* Hover effect (when editable) */
.course-block:hover {
  @apply shadow-lg scale-105;
}

/* Conflict indicator */
.course-block.conflict {
  @apply ring-2 ring-red-500;
}
```

### Color Assignment

Colors are assigned sequentially from the palette:

```typescript
const courseColors = new Map<string, string>();
let colorIndex = 0;

sections.forEach(section => {
  if (!courseColors.has(section.course_id)) {
    courseColors.set(
      section.course_id, 
      COLOR_PALETTE[colorIndex % COLOR_PALETTE.length]
    );
    colorIndex++;
  }
});
```

## Integration with Backend API

### Expected API Response

When calling `/api/schedule/optimize` or `/api/chat/message`, the backend should return:

```typescript
{
  "schedules": [
    {
      "sections": [
        {
          "id": "uuid",
          "course_id": "uuid",
          "section_number": "CSC 101",
          "professor_name": "Dr. Johnson",
          "days": "MWF",
          "start_time": "10:00",
          "end_time": "11:00",
          "location": "NAC 5/150",
          "modality": "In-person",
          "enrolled": 25,
          "capacity": 30
        }
      ],
      "score": 95,
      "conflicts": []
    }
  ]
}
```

### Updating Calendar from API

```typescript
const handleOptimize = async () => {
  const response = await fetch('/api/schedule/optimize', {
    method: 'POST',
    body: JSON.stringify({
      course_codes: ['CSC 101', 'MAT 201'],
      semester: 'Fall 2025',
      constraints: {...}
    })
  });
  
  const data = await response.json();
  
  // Update calendar with first schedule
  if (data.schedules && data.schedules.length > 0) {
    await updateFromAI(data.schedules[0]);
  }
};
```

## Testing

### Unit Tests

Test the grid rendering:

```typescript
describe('ScheduleGrid', () => {
  it('renders time slots correctly', () => {
    render(<ScheduleGrid sections={[]} />);
    expect(screen.getByText('8:00 AM')).toBeInTheDocument();
  });
  
  it('displays courses in correct positions', () => {
    const sections = [mockSection];
    render(<ScheduleGrid sections={sections} />);
    // Assert course is rendered at correct position
  });
  
  it('shows conflict indicators', () => {
    const conflicts = [mockConflict];
    render(<ScheduleGrid sections={[]} conflicts={conflicts} />);
    expect(screen.getByText(/conflict/i)).toBeInTheDocument();
  });
});
```

### Integration Tests

Test the full flow:

```typescript
describe('AI Schedule Integration', () => {
  it('updates calendar when AI suggests schedule', async () => {
    const { updateFromAI } = renderHook(() => useScheduleGrid());
    
    await updateFromAI(mockAIResponse);
    
    expect(updateFromAI.result.current.sections).toHaveLength(3);
  });
});
```

## Troubleshooting

### Issue: Courses not appearing

**Solution**: Check that sections have valid `days`, `start_time`, and `end_time` fields.

### Issue: Incorrect positioning

**Solution**: Verify time format is correct (either "HH:MM" or "HH:MM AM/PM").

### Issue: Conflicts not detected

**Solution**: Ensure section IDs are valid and `checkScheduleConflicts` is being called.

### Issue: Colors not distinct

**Solution**: Check that `course_id` is unique for each course.

## Future Enhancements

1. **Drag and Drop**: Allow users to drag courses to different time slots
2. **Multi-week View**: Support viewing multiple weeks
3. **Export**: Export schedule as PDF or image
4. **Print Optimization**: Better print styling
5. **Accessibility**: Enhanced keyboard navigation and screen reader support
6. **Mobile Gestures**: Swipe to navigate between days
7. **Custom Colors**: Allow users to choose course colors
8. **Notes**: Add notes to specific time slots

## Conclusion

The enhanced ScheduleGrid component provides a robust, flexible calendar view that seamlessly integrates with AI-generated schedules. The combination of the ScheduleGrid component and useScheduleGrid hook makes it easy to display and update schedules dynamically, with automatic conflict detection and smooth transitions.
