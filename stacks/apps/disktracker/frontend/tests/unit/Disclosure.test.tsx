import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MantineProvider } from '@mantine/core';
import { Disclosure } from '../../src/Disclosure';

afterEach(cleanup);

it('hides its content behind a counted toggle until opened, and hides it again when closed', async () => {
  const user = userEvent.setup();
  render(<MantineProvider env="test"><Disclosure label="Price history" count={3}><p>Hidden rows</p></Disclosure></MantineProvider>);
  const toggle = screen.getByRole('button', { name: 'Price history (3)' });
  expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(screen.queryByText('Hidden rows')).not.toBeInTheDocument();
  await user.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByText('Hidden rows')).toBeVisible();
  await user.click(toggle);
  expect(screen.queryByText('Hidden rows')).not.toBeInTheDocument();
});

it('names the toggle by its label alone when there is nothing to count', () => {
  render(<MantineProvider env="test"><Disclosure label="Specifications"><p>Specs</p></Disclosure></MantineProvider>);
  expect(screen.getByRole('button', { name: 'Specifications' })).toHaveAttribute('aria-expanded', 'false');
});
