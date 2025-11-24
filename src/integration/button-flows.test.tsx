import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OptimizeButton } from '@/components/ui/optimize-button';
import { ChatButton } from '@/components/ui/chat-button';
import { ProfessorButton } from '@/components/ui/professor-button';
import * as apiEndpoints from '@/lib/api-endpoints';

// Mock API endpoints
jest.mock('@/lib/api-endpoints');

describe('Button Integration Flows', () => {

    describe('OptimizeButton', () => {
        it('should trigger optimization and handle response', async () => {
            const mockResponse = {
                schedules: [],
                count: 0,
                courses: {},
                total_sections: 0
            };

            (apiEndpoints.optimizeSchedule as jest.Mock).mockResolvedValue(mockResponse);

            const onOptimized = jest.fn();

            render(
                <OptimizeButton
                    courseCodes={['CSC 101']}
                    onOptimized={onOptimized}
                />
            );

            fireEvent.click(screen.getByText(/AI Optimize/i));

            await waitFor(() => {
                expect(apiEndpoints.optimizeSchedule).toHaveBeenCalled();
                expect(onOptimized).toHaveBeenCalledWith(mockResponse);
            });
        });
    });

    describe('ChatButton', () => {
        it('should send message and receive response', async () => {
            const mockResponse = {
                message: 'Hello',
                suggestedSchedule: null
            };

            (apiEndpoints.sendChatMessage as jest.Mock).mockResolvedValue(mockResponse);

            const onResponse = jest.fn();

            render(
                <ChatButton
                    message="Hi"
                    onResponse={onResponse}
                />
            );

            fireEvent.click(screen.getByRole('button'));

            await waitFor(() => {
                expect(apiEndpoints.sendChatMessage).toHaveBeenCalled();
                expect(onResponse).toHaveBeenCalledWith(mockResponse);
            });
        });
    });

    describe('ProfessorButton', () => {
        it('should fetch professor details on click', async () => {
            const mockProfessor = {
                id: '1',
                name: 'Dr. Smith',
                department: 'CS'
            };

            (apiEndpoints.getProfessorByNameAPI as jest.Mock).mockResolvedValue(mockProfessor);

            const onDataLoaded = jest.fn();

            render(
                <ProfessorButton
                    professorName="Dr. Smith"
                    onDataLoaded={onDataLoaded}
                />
            );

            fireEvent.click(screen.getByText('Dr. Smith'));

            await waitFor(() => {
                expect(apiEndpoints.getProfessorByNameAPI).toHaveBeenCalledWith('Dr. Smith');
                expect(onDataLoaded).toHaveBeenCalledWith(mockProfessor);
            });
        });
    });
});
