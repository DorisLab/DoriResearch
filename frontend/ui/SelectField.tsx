import * as Select from '@radix-ui/react-select';
import { Fragment } from 'react';
import { Check } from '@phosphor-icons/react/dist/csr/Check';
import { CaretDown as ChevronDown } from '@phosphor-icons/react/dist/csr/CaretDown';
import { CaretUp as ChevronUp } from '@phosphor-icons/react/dist/csr/CaretUp';
import './select-field.css';

export interface SelectOption {
  value: string;
  label: string;
  caption?: string;
  disabled?: boolean;
  separatorAfter?: boolean;
}
export function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  disabled,
  className = '',
  menuClassName = '',
}: {
  id?: string;
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  menuClassName?: string;
}) {
  return (
    <Select.Root value={value} onValueChange={onChange} disabled={disabled}>
      <Select.Trigger
        id={id}
        aria-label={label}
        className={`select-trigger ${options.some((o) => o.caption) ? 'select-with-caption' : ''} ${className}`}
      >
        <Select.Value placeholder="请选择" />
        <Select.Icon asChild>
          <ChevronDown className="ui-icon" weight="light" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content
          className={`select-menu ${menuClassName}`}
          position="popper"
          align="end"
          sideOffset={5}
          collisionPadding={12}
          onEscapeKeyDown={(event) => event.stopPropagation()}
        >
          <Select.ScrollUpButton className="select-scroll">
            <ChevronUp className="ui-icon" weight="light" />
          </Select.ScrollUpButton>
          <Select.Viewport className="select-viewport">
            <SelectOptions options={options} />
          </Select.Viewport>
          <Select.ScrollDownButton className="select-scroll">
            <ChevronDown className="ui-icon" weight="light" />
          </Select.ScrollDownButton>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}

function SelectOptions({ options }: { options: SelectOption[] }) {
  return options.map((option) => (
    <Fragment key={option.value}>
      <Select.Item
        className="select-option"
        value={option.value}
        disabled={option.disabled}
        textValue={option.label}
      >
        <Select.ItemText>
          {option.caption ? (
            <span className="select-option-text">
              <span>{option.label}</span>
              <small>{option.caption}</small>
            </span>
          ) : (
            option.label
          )}
        </Select.ItemText>
        <Select.ItemIndicator className="select-check">
          <Check className="ui-icon" weight="light" />
        </Select.ItemIndicator>
      </Select.Item>
      {option.separatorAfter && <Select.Separator className="select-separator" />}
    </Fragment>
  ));
}
