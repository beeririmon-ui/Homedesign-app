/**
 * S19, QA ת53: the errors our own code throws. Only these give a log row (lib/log.ts `errorCode`) a code from their
 * `code`, the snake_case code their message starts with, or their class name. Any other error (a provider's, a
 * library's) is logged by its HTTP status, a system code (ECONNRESET), a timeout, or the standard name of its class
 * (TypeError…), else 'Error': a provider's own text, its message prefix or a class name it chose ('Orna'), never.
 * A leaf module (no imports), so every class of ours can extend it without a cycle.
 */
export class OwnError extends Error {}

/**
 * An error of our own code with a code of its own (a snake_case word): its message is `<code>: <detail>`, as our code
 * wrote them before S19 ("set_composition_missing: <variant>").
 */
export class CodedError extends OwnError {
  constructor(
    public readonly code: string,
    detail?: string,
  ) {
    super(detail ? `${code}: ${detail}` : code);
    this.name = 'CodedError';
  }
}
