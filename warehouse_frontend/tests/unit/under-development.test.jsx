import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import UnderDevelopmentPage from '../../src/components/common/UnderDevelopmentPage';

describe('UnderDevelopmentPage Component', () => {
  it('should render title, badge and description correctly', () => {
    render(
      <MemoryRouter>
        <UnderDevelopmentPage
          title="Add Rack"
          moduleName="Racks"
          backTo="/racks"
        />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: 'Add Rack' })).toBeInTheDocument();
    expect(screen.getByText(/Under Development/i)).toBeInTheDocument();
    expect(screen.getByText(/Add Rack Form Coming Soon/i)).toBeInTheDocument();
    expect(screen.getByText(/Back to Racks/i)).toBeInTheDocument();
    expect(screen.getByText(/Go to Dashboard/i)).toBeInTheDocument();
  });

  it('should navigate back when Back button is clicked', () => {
    render(
      <MemoryRouter initialEntries={['/racks', '/racks/new']}>
        <UnderDevelopmentPage
          title="Add Bin"
          moduleName="Bins"
          backTo="/bins"
        />
      </MemoryRouter>
    );

    const backButton = screen.getByRole('button', { name: /Back to Bins/i });
    expect(backButton).toBeInTheDocument();
    fireEvent.click(backButton);
  });
});
