import { useCallback, useEffect, useState } from 'react';
import { ActionIcon, Alert, Button, Group, NativeSelect, Table, Text, TextInput } from '@mantine/core';
import { ApiValidationError, type Condition, type ConditionRule, type ListingsApi } from './api';
import { conditions } from './listing-display';

type Props = { api: ListingsApi };

/** Which text names which condition. The collector and pasted listings read them in order, against
 * an offer's title and the store's own condition field; the first rule that matches wins. */
export function ConditionRulesSection({ api }: Props) {
  const [rules, setRules] = useState<ConditionRule[] | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => {
    try { setRules(await api.listConditionRules()); }
    catch (err) { setError(err instanceof Error ? err.message : 'Condition rules could not be loaded.'); }
  }, [api]);
  useEffect(() => { void load(); }, [load]);
  const change = (next: ConditionRule[]) => { setRules(next); setNotice(''); };
  const update = (index: number, rule: Partial<ConditionRule>) =>
    change((rules ?? []).map((current, at) => at === index ? { ...current, ...rule } : current));
  const moveUp = (index: number) => {
    const next = [...(rules ?? [])];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    change(next);
  };
  const save = async () => {
    setSaving(true); setErrors({}); setError('');
    try {
      setRules(await api.replaceConditionRules(rules ?? []));
      setNotice('Condition rules saved.');
    } catch (err) {
      if (err instanceof ApiValidationError) setErrors(err.fields);
      else setError(err instanceof Error ? err.message : 'Condition rules could not be saved.');
    } finally { setSaving(false); }
  };
  return <section aria-labelledby="condition-rules-heading" className="admin-section">
    <h2 id="condition-rules-heading">Condition rules</h2>
    <Text size="sm" c="dimmed" mb="xs">
      Read in order against an offer's title and the store's condition field; the first pattern that matches
      names the condition. Patterns are case-insensitive regular expressions; <code>\b</code> marks a word boundary.
    </Text>
    {error && <Alert color="red" role="alert" mb="sm">{error}</Alert>}
    {rules !== null && <>
      <div className="sheet-scroll"><Table aria-label="Condition rules">
        <Table.Thead><Table.Tr><Table.Th>#</Table.Th><Table.Th>Pattern</Table.Th><Table.Th>Condition</Table.Th><Table.Th /></Table.Tr></Table.Thead>
        <Table.Tbody>{rules.map((rule, index) => {
          const number = index + 1;
          return <Table.Tr key={index}>
            <Table.Td className="numeric">{number}</Table.Td>
            <Table.Td><TextInput aria-label={`Pattern ${number}`} value={rule.pattern} error={errors[`${index}.pattern`]}
              onChange={event => update(index, { pattern: event.currentTarget.value })} /></Table.Td>
            <Table.Td><NativeSelect aria-label={`Condition ${number}`} data={conditions} value={rule.condition}
              error={errors[`${index}.condition`]} onChange={event => update(index, { condition: event.currentTarget.value as Condition })} /></Table.Td>
            <Table.Td><Group gap="sm" wrap="nowrap">
              <ActionIcon variant="subtle" aria-label={`Move rule ${number} up`} disabled={index === 0} onClick={() => moveUp(index)}>↑</ActionIcon>
              <ActionIcon variant="subtle" color="red" aria-label={`Remove rule ${number}`}
                onClick={() => change(rules.filter((_, at) => at !== index))}>✕</ActionIcon>
            </Group></Table.Td>
          </Table.Tr>;
        })}</Table.Tbody>
      </Table></div>
      <Group gap="xs" mt="sm">
        <Button variant="default" onClick={() => change([...rules, { pattern: '', condition: 'new' }])}>Add rule</Button>
        <Button onClick={save} loading={saving}>Save rules</Button>
        {notice && <Text size="sm" role="status">{notice}</Text>}
      </Group>
    </>}
  </section>;
}
