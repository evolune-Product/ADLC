import { Reveal, SplitHeading } from '../Reveal'
import { SectionHead } from '../ui'
import { POSITIONING } from '../content'

/**
 * "Where does this sit next to the thing I already use?"
 *
 * It is the question every evaluator asks within the first minute, and a page
 * that refuses to answer it gets the answer invented on its behalf. So it is
 * answered directly — and narrowly. The table compares *design intent* across
 * three categories, never quality, never speed, and the disclaimer under it
 * says so in as many words rather than in a footnote nobody reads.
 *
 * The honest position is also the stronger one: most of these buyers are
 * already using something in the first column and should keep it. Evolune OS governs
 * what reaches production. It is not trying to be the editor.
 */
export function Positioning() {
  const { columns, rows, disclaimer } = POSITIONING

  return (
    <section id="positioning" className="mk-section">
      <div className="mk-shell">
        <SectionHead
          n="02"
          eyebrow="Where this sits"
          standfirst="Three different bets on what the bottleneck is. The first two assume it is writing the code. This one assumes it stopped being that a while ago."
        >
          <SplitHeading
            text="Not another way to write code."
            highlight={['write', 'code.']}
            className="mk-display text-[clamp(30px,4.4vw,56px)]"
          />
        </SectionHead>

        <Reveal className="mt-14">
          {/* Wide content scrolls inside its own container rather than pushing
              the page sideways. */}
          <div className="-mx-[var(--mk-gutter)] overflow-x-auto px-[var(--mk-gutter)] pb-2">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <caption className="sr-only">
                How Evolune OS differs by design from IDE assistants and autonomous coding agents
              </caption>
              <thead>
                <tr className="border-b border-[var(--mk-hairline-lit)]">
                  <th scope="col" className="w-[19%] py-4 pr-6">
                    <span className="mk-readout-label">By design</span>
                  </th>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      scope="col"
                      className={
                        col.key === 'adlc'
                          ? 'w-[27%] rounded-t-xl border-x border-t border-[var(--mk-ember)]/30 bg-[var(--mk-wash-1)] py-4 pl-4 pr-4 align-bottom'
                          : 'w-[27%] py-4 pr-6 align-bottom'
                      }
                    >
                      <div
                        className={
                          col.key === 'adlc'
                            ? 'mk-mono text-[13px] font-semibold uppercase tracking-[0.14em] text-[var(--mk-ember-lit)]'
                            : 'mk-mono text-[13px] uppercase tracking-[0.14em] text-[var(--mk-ink)]'
                        }
                      >
                        {col.label}
                      </div>
                      <div className="mt-1 text-[12px] font-normal text-[var(--mk-ink-3)]">
                        {col.note}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={row.question} className="border-b border-[var(--mk-hairline)] align-top">
                    <th scope="row" className="py-5 pr-6 text-[13.5px] font-medium text-[var(--mk-ink-2)]">
                      {row.question}
                    </th>
                    <td className="py-5 pr-6 text-[14px] leading-snug text-[var(--mk-ink-3)]">
                      {row.ide}
                    </td>
                    <td className="py-5 pr-6 text-[14px] leading-snug text-[var(--mk-ink-3)]">
                      {row.agent}
                    </td>
                    {/* The one column that is allowed to be lit — a
                        continuous ember-bordered panel running down the
                        table, not just a flat wash, so it reads as "us" at
                        a glance rather than on a read of every row. */}
                    <td
                      className={
                        'border-x border-[var(--mk-ember)]/30 bg-[var(--mk-wash-1)] py-5 pl-4 pr-4 ' +
                        'text-[14px] leading-snug text-[var(--mk-ink)] ' +
                        (i === rows.length - 1 ? 'rounded-b-xl border-b' : '')
                      }
                    >
                      {row.adlc}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <p className="mt-8 max-w-[78ch] text-[13.5px] leading-relaxed text-[var(--mk-ink-3)]">
            {disclaimer}
          </p>
        </Reveal>
      </div>
    </section>
  )
}
