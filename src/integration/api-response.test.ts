import { describe, it, expect, vi } from 'vitest';
import { searchCoursesAPI, getProfessorByNameAPI, compareProfessors } from '../lib/api-endpoints';
import { apiClient } from '../lib/api-client';

// Mock apiClient
vi.mock('../lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('API Response Handling', () => {
  it('searchCoursesAPI unwraps data from standardized response', async () => {
    const mockResponse = {
      data: {
        courses: [{ id: '1', name: 'Intro to CS' }],
        count: 1
      },
      metadata: {
        source: 'hybrid',
        is_fresh: true
      }
    };
    
    (apiClient.get as any).mockResolvedValue(mockResponse);
    
    const result = await searchCoursesAPI({ query: 'CS' });
    
    expect(result).toEqual(mockResponse.data);
  });

  it('getProfessorByNameAPI unwraps data from standardized response', async () => {
    const mockResponse = {
      data: {
        id: '123',
        name: 'John Doe'
      },
      metadata: {
        source: 'hybrid',
        is_fresh: true
      }
    };
    
    (apiClient.get as any).mockResolvedValue(mockResponse);
    
    const result = await getProfessorByNameAPI('John Doe');
    
    expect(result).toEqual(mockResponse.data);
  });
  
  it('compareProfessors unwraps data from standardized response', async () => {
    const mockResponse = {
      data: {
        success: true,
        recommendation: 'Prof A'
      },
      metadata: {
        source: 'hybrid',
        is_fresh: true
      }
    };
    
    (apiClient.post as any).mockResolvedValue(mockResponse);
    
    const result = await compareProfessors(['Prof A', 'Prof B']);
    
    expect(result).toEqual(mockResponse.data);
  });
});
