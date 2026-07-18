import { zodResolver } from '@hookform/resolvers/zod';
import type { FieldValues, Resolver } from 'react-hook-form';
import type { ZodType } from 'zod';

/**
 * Typed helper that wires a Zod schema into react-hook-form's resolver API,
 * so every form in the app validates the same way.
 *
 * @example
 *   const resolver = createSchemaResolver(passengerSchema);
 *   useForm({ resolver });
 */
export function createSchemaResolver<TFieldValues extends FieldValues>(
  schema: ZodType<TFieldValues>,
): Resolver<TFieldValues> {
  return zodResolver(schema) as Resolver<TFieldValues>;
}

export { zodResolver };
