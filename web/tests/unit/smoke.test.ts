import { describe, expect, it } from 'vitest';

import { add } from '../../src/utils/add';
import { testWrapperTimeout } from '../testWrapperTimeout';

const run = testWrapperTimeout(async () => {
  const result = add(2, 3);
  expect(result).toBe(5);
});
(run as { testName?: string }).testName = 'adds two numbers';

describe('smoke', () => {
  it('adds two numbers', run);
});
