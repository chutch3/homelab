import { useState, type ReactNode } from 'react';
import { Button } from '@mantine/core';

type Props = { label: string; count?: number; startOpen?: boolean; children: ReactNode };

export function Disclosure({ label, count, startOpen = false, children }: Props) {
  const [open, setOpen] = useState(startOpen);
  return <div className="disclosure">
    <Button variant="subtle" aria-expanded={open} onClick={() => setOpen(!open)}
      leftSection={<span aria-hidden="true">{open ? '▾' : '▸'}</span>}>{count === undefined ? label : `${label} (${count})`}</Button>
    {open && children}
  </div>;
}
