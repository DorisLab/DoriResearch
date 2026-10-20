import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { SavedTime } from './SavedTime';

it('保存时间使用主题提示，键盘关闭保留焦点，窗口失焦关闭提示', async () => {
  const user = userEvent.setup();
  const { container } = render(<SavedTime value={Date.UTC(2026, 9, 21)} />);
  const time = container.querySelector('time')!;
  expect(time).not.toHaveAttribute('title');
  await user.tab();
  // jsdom has no layout; Radix hides the zero-sized anchor's popup visually.
  expect(await screen.findByRole('tooltip', { hidden: true })).toHaveTextContent('最近保存时间');
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('tooltip', { hidden: true })).not.toBeInTheDocument();
  expect(time).toHaveFocus();
  fireEvent.blur(time);
  fireEvent.focus(time);
  expect(await screen.findByRole('tooltip', { hidden: true })).toBeInTheDocument();
  fireEvent(window, new Event('blur'));
  await waitFor(() =>
    expect(screen.queryByRole('tooltip', { hidden: true })).not.toBeInTheDocument(),
  );
});
