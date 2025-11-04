import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ScheduleEvent {
  id: string;
  course_code: string;
  course_name: string;
  professor: string;
  location: string;
  start_time: string;
  end_time: string;
  color: string;
}

interface ScheduleGridProps {
  events?: ScheduleEvent[];
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const TIME_SLOTS = [
  '8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM', '12:00 PM',
  '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM', '5:00 PM', '6:00 PM'
];

export default function ScheduleGrid({ 
  events = [
    {
      id: "1",
      course_code: "CSC 381",
      course_name: "Algorithms",
      professor: "Dr. Johnson",
      location: "NAC 5/150",
      start_time: "10:00 AM",
      end_time: "11:15 AM",
      color: "bg-blue-500"
    },
    {
      id: "2",
      course_code: "MATH 301",
      course_name: "Linear Algebra",
      professor: "Prof. Smith",
      location: "NAC 6/113",
      start_time: "2:00 PM",
      end_time: "3:30 PM",
      color: "bg-green-500"
    }
  ]
}: ScheduleGridProps) {
  const timeToMinutes = (time: string): number => {
    const [timePart, period] = time.split(' ');
    let [hours, minutes] = timePart.split(':').map(Number);
    
    if (period === 'PM' && hours !== 12) hours += 12;
    if (period === 'AM' && hours === 12) hours = 0;
    
    return hours * 60 + (minutes || 0);
  };

  const getEventPosition = (startTime: string, endTime: string) => {
    const startMinutes = timeToMinutes(startTime);
    const endMinutes = timeToMinutes(endTime);
    const baseMinutes = timeToMinutes('8:00 AM');
    
    const top = ((startMinutes - baseMinutes) / 60) * 80;
    const height = ((endMinutes - startMinutes) / 60) * 80;
    
    return { top, height };
  };

  const getDayEvents = (day: string) => {
    return events.filter(event => {
      // This is simplified - in real app, you'd check the days field
      return true;
    });
  };

  return (
    <Card className="w-full bg-white">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-gray-900">Weekly Schedule</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="min-w-[800px]">
            {/* Header with days */}
            <div className="grid grid-cols-6 gap-2 mb-2">
              <div className="text-sm font-semibold text-gray-600 p-2">Time</div>
              {DAYS.map(day => (
                <div key={day} className="text-sm font-semibold text-gray-900 p-2 text-center bg-gray-50 rounded">
                  {day}
                </div>
              ))}
            </div>

            {/* Time slots grid */}
            <div className="relative">
              {TIME_SLOTS.map((time, idx) => (
                <div key={time} className="grid grid-cols-6 gap-2 border-t border-gray-200" style={{ height: '80px' }}>
                  <div className="text-xs text-gray-600 p-2">{time}</div>
                  {DAYS.map(day => (
                    <div key={`${day}-${time}`} className="border-l border-gray-100 relative">
                      {/* Events will be positioned absolutely here */}
                    </div>
                  ))}
                </div>
              ))}

              {/* Sample events - positioned absolutely */}
              <div className="absolute top-[160px] left-[calc(16.666%+0.5rem)] w-[calc(16.666%-1rem)] z-10">
                <div className="bg-blue-500 text-white p-2 rounded shadow-md h-[100px]">
                  <div className="font-semibold text-sm">CSC 381</div>
                  <div className="text-xs mt-1">Algorithms</div>
                  <div className="text-xs">Dr. Johnson</div>
                  <div className="text-xs">NAC 5/150</div>
                </div>
              </div>

              <div className="absolute top-[160px] left-[calc(50%+0.5rem)] w-[calc(16.666%-1rem)] z-10">
                <div className="bg-blue-500 text-white p-2 rounded shadow-md h-[100px]">
                  <div className="font-semibold text-sm">CSC 381</div>
                  <div className="text-xs mt-1">Algorithms</div>
                  <div className="text-xs">Dr. Johnson</div>
                  <div className="text-xs">NAC 5/150</div>
                </div>
              </div>

              <div className="absolute top-[480px] left-[calc(33.333%+0.5rem)] w-[calc(16.666%-1rem)] z-10">
                <div className="bg-green-500 text-white p-2 rounded shadow-md h-[120px]">
                  <div className="font-semibold text-sm">MATH 301</div>
                  <div className="text-xs mt-1">Linear Algebra</div>
                  <div className="text-xs">Prof. Smith</div>
                  <div className="text-xs">NAC 6/113</div>
                </div>
              </div>

              <div className="absolute top-[480px] left-[calc(66.666%+0.5rem)] w-[calc(16.666%-1rem)] z-10">
                <div className="bg-green-500 text-white p-2 rounded shadow-md h-[120px]">
                  <div className="font-semibold text-sm">MATH 301</div>
                  <div className="text-xs mt-1">Linear Algebra</div>
                  <div className="text-xs">Prof. Smith</div>
                  <div className="text-xs">NAC 6/113</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 flex gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span className="text-sm text-gray-700">CSC 381 - Algorithms</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span className="text-sm text-gray-700">MATH 301 - Linear Algebra</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}