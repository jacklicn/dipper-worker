/**
 * Sample external tool-pack entry.
 * Copy this folder to `<workspace>/plugins/echo-pack`.
 *
 * Runs in the shared plugin-host child process (all external packs share one process).
 * Exports `contribute(sink)` — sink matches ToolRegistry.register / registerAll.
 */
function contribute(sink) {
  sink.register({
    name: 'example_echo',
    description: 'Echo a string (sample external pack).',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Text to echo' },
      },
      required: ['text'],
    },
    async execute(params) {
      return String(params.text ?? '')
    },
  })
}

module.exports = { contribute }
