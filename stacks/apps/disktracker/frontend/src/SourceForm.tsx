import { useState } from 'react';
import { Alert, Button, Checkbox, Group, Modal, NativeSelect, Stack, Text, Textarea, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { ApiValidationError, type InspectionCandidate, type ListingsApi, type SettingDescription, type Source, type SourceBasis, type SourceInput, type SourceKindDescription, type SourcePreview, type SourceSettings, type SourceTransport } from './api';
import { Disclosure } from './Disclosure';
import { LinkInspector } from './LinkInspector';
import { SourcePreviewResult } from './SourcePreviewResult';
import { sourceBases } from './SourcesSection';

type Props = {
  api: ListingsApi;
  /** The kinds of store there are, each as its reader describes it: the form asks for what the chosen one has. */
  kinds: SourceKindDescription[];
  /** The source to edit, or null to add one. */
  source: Source | null;
  onClose: () => void; onSaved: () => Promise<void>;
  /** Asked to delete the store being edited; deleting is confirmed apart from this form. */
  onDelete?: (source: Source) => void;
};
const transports: { value: SourceTransport; label: string }[] = [
  { value: 'direct', label: 'Directly' },
  { value: 'browser', label: 'Through a browser (FlareSolverr)' },
];
type Values = {
  name: string; kind: string; base_url: string; schedule: string; transport: string; basis: string; notes: string;
  settings: Record<string, string | boolean>;
  /** Only for Test: one page to read instead of those the sitemap lists. Never saved. */
  page_url: string;
};
const formSettings = (settings: SourceSettings = {}) => Object.fromEntries(Object.entries(settings)
  .map(([name, value]) => [name, Array.isArray(value) ? value.join(', ') : value]));
/** The kind's settings as the API takes them: lists split on commas, blank text left to the defaults. */
function sourceSettings(fields: SettingDescription[], values: Record<string, string | boolean>): SourceSettings {
  return Object.fromEntries(fields.flatMap(({ name, type }): [string, string | boolean | string[]][] => {
    const value = values[name];
    if (type === 'flag') return [[name, value === true]];
    const text = typeof value === 'string' ? value : '';
    if (type === 'list') return [[name, text.split(',').map(part => part.trim()).filter(Boolean)]];
    // Kept as typed: a title prefix can end in a meaningful space.
    return text.trim() ? [[name, text]] : [];
  }));
}

export function SourceForm({ api, kinds, source, onClose, onSaved, onDelete }: Props) {
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [preview, setPreview] = useState<SourcePreview | null>(null);
  const [error, setError] = useState('');
  const form = useForm<Values>({
    initialValues: {
      name: source?.name ?? '', kind: source?.kind ?? '', base_url: source?.base_url ?? '',
      schedule: source?.schedule ?? '0 */8 * * *', transport: source?.transport ?? 'direct', basis: source?.basis ?? 'unconfirmed', notes: source?.notes ?? '',
      settings: formSettings(source?.settings), page_url: '',
    },
  });
  /** The kind chosen, as it is described; undefined until one is. */
  const kind = kinds.find(known => known.kind === form.values.kind);
  const fields = kind?.settings ?? [];
  const inputOf = (values: Values): SourceInput => ({
    name: values.name.trim(), kind: values.kind, base_url: values.base_url.trim(),
    settings: sourceSettings(fields, values.settings),
    schedule: values.schedule.trim(), enabled: source?.enabled ?? true, transport: values.transport as SourceTransport,
    basis: values.basis as SourceBasis, notes: values.notes.trim(),
  });
  /** Sends the form as it stands; the API's complaints land on the fields they are about. */
  const sending = async (send: (input: SourceInput) => Promise<void>, fallback: string) => {
    setError(''); form.clearErrors();
    try { await send(inputOf(form.values)); }
    catch (err) {
      if (err instanceof ApiValidationError) form.setErrors(err.fields);
      else setError(err instanceof Error ? err.message : fallback);
    }
  };
  const submit = form.onSubmit(async () => {
    setSaving(true);
    await sending(async input => {
      if (source) await api.updateSource(source.id, input); else await api.addSource(input);
      await onSaved();
    }, 'The store could not be saved.');
    setSaving(false);
  });
  const test = async () => {
    setTesting(true); setPreview(null);
    const page = kind?.page_test ? form.values.page_url.trim() : '';
    await sending(async input => setPreview(await api.previewSource(page ? { ...input, page_url: page } : input)), 'The store could not be tested.');
    setTesting(false);
  };
  /** Takes a way of reading the store found by inspecting a link: its kind, address and settings, the
   * link as the page Test reads, and a name from the address unless one is entered. */
  const use = (candidate: InspectionCandidate, baseUrl: string, link: string) => {
    const host = new URL(baseUrl).hostname.replace(/^www\./, '').split('.')[0];
    form.setValues({
      kind: candidate.kind, base_url: baseUrl, settings: formSettings(candidate.settings), page_url: link,
      name: form.values.name.trim() || host.charAt(0).toUpperCase() + host.slice(1),
    });
    setPreview(null);
  };
  const title = source ? 'Edit store' : 'Add store';
  // A store entered by hand is never collected, so it needs no address, schedule or basis.
  const collected = kind?.collected ?? true;
  const settingInput = (field: SettingDescription) => field.type === 'flag'
    ? <Checkbox key={field.name} label={field.label} aria-label={field.label}
      {...form.getInputProps(`settings.${field.name}`, { type: 'checkbox' })} />
    : <TextInput key={field.name} label={field.label} aria-label={field.label} placeholder={field.placeholder || undefined}
      description={field.description || undefined} {...form.getInputProps(`settings.${field.name}`)} value={String(form.values.settings[field.name] ?? '')} />;
  return <Modal opened title={title} size="lg" onClose={() => { if (!saving) onClose(); }} centered>
    <form onSubmit={submit} noValidate><Stack>
      {!source && <LinkInspector api={api} transport={form.values.transport as SourceTransport} onUse={use} />}
      <TextInput label="Name" aria-label="Name" required maxLength={80} {...form.getInputProps('name')} />
      <NativeSelect label="Type" aria-label="Type" required data={[{ value: '', label: 'Choose type' }, ...kinds.map(known => ({ value: known.kind, label: known.label }))]} {...form.getInputProps('kind')} />
      <TextInput label="Store URL" aria-label="Store URL" type="url" required={collected} placeholder="https://www.example.com" {...form.getInputProps('base_url')} />
      {/* What must be given is asked for at once; what can be left blank waits under Advanced, in its groups. */}
      {fields.filter(field => field.required).map(settingInput)}
      <Disclosure label="Advanced"><Stack>
        {fields.filter(field => !field.required && !field.group).map(settingInput)}
        {(kind?.groups ?? []).map(group => {
          const grouped = fields.filter(field => !field.required && field.group === group.name);
          // Open already when the store being edited has something set in it.
          const set = grouped.some(field => Boolean(source?.settings[field.name]) && source?.settings[field.name] !== '');
          return <Disclosure key={group.name} label={group.label} startOpen={set}><Stack>
            <Text size="sm" c="dimmed">{group.help}</Text>
            {grouped.map(settingInput)}
          </Stack></Disclosure>;
        })}
        {collected && <>
        <TextInput label="Schedule (cron)" aria-label="Schedule (cron)" required placeholder="0 */8 * * *"
          description="Minute hour day month weekday, in UTC; every 8 hours unless changed" {...form.getInputProps('schedule')} />
        <NativeSelect label="Fetch pages" aria-label="Fetch pages" data={transports}
          description="Through a browser only for stores that refuse the collector; it cannot identify itself there" {...form.getInputProps('transport')} />
        <NativeSelect label="Permission" aria-label="Permission" data={sourceBases}
          description="What allows collecting from it; shown on the Stores list, not enforced" {...form.getInputProps('basis')} />
        </>}
        <Textarea label="Notes" aria-label="Notes" maxLength={2000} autosize minRows={2} {...form.getInputProps('notes')} />
      </Stack></Disclosure>
      {kind?.page_test && <TextInput label="Page to test" aria-label="Page to test" type="url"
        placeholder="https://www.example.com/a-product-page" {...form.getInputProps('page_url')}
        description="Optional, and not saved: Test reads this one page instead of the first few the sitemap lists" />}
      {preview && <SourcePreviewResult preview={preview} />}
      {error && <Alert color="red" role="alert">{error}</Alert>}
      <Group justify="space-between">
        <Group>
          {collected && form.values.kind && <Button variant="default" onClick={test} loading={testing} disabled={saving}
            title="Read one offer from the store now, without saving anything">Test</Button>}
          {/* Other is always kept, for one-off stores. */}
          {source && source.key !== 'other' && onDelete && <Button variant="subtle" color="red" disabled={saving || testing}
            onClick={() => onDelete(source)}>Delete store</Button>}
        </Group>
        <Group>
          <Button variant="default" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" loading={saving} disabled={testing}>Save</Button>
        </Group>
      </Group>
    </Stack></form>
  </Modal>;
}
