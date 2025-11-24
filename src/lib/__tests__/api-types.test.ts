import { ScheduleOptimizationRequest } from '../api-endpoints';

describe('API Type Definitions', () => {
    it('should create valid ScheduleOptimizationRequest', () => {
        const request: ScheduleOptimizationRequest = {
            courseCodes: ['CSC 101'],
            semester: 'Fall 2025',
            constraints: {
                earliestStartTime: '09:00',
                latestEndTime: '17:00',
            },
        };

        expect(request).toBeDefined();
        expect(request.courseCodes).toContain('CSC 101');
    });
});
