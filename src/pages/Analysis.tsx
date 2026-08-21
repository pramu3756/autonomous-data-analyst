import { useEffect, useState } from 'react';
import {
  Loader2,
  Sparkles,
  MessageCircle,
  Send,
  AlertCircle,
} from 'lucide-react';

import {
  analyze,
  askQuestion,
} from '@/services/api';

import { useDataset } from '@/services/datasetContext';

import type {
  AnalysisResult,
  QuestionResult,
} from '@/services/api';

import ChartRenderer from '@/charts/ChartRenderer';

export default function Analysis() {
  const { datasetId } = useDataset();

  const [data, setData] =
    useState<AnalysisResult | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [step, setStep] =
    useState(0);

  const [question, setQuestion] =
    useState('');

  const [qResult, setQResult] =
    useState<QuestionResult | null>(null);

  const [qLoading, setQLoading] =
    useState(false);

  const [qError, setQError] =
    useState<string | null>(null);

  const STEPS = [
    'Analyzing dataset...',
    'Calculating statistics...',
    'Detecting relationships...',
    'Generating visualizations...',
  ];

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      setError('No dataset is selected.');
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);
    setStep(0);

    const timer = window.setInterval(() => {
      setStep((current) =>
        current < STEPS.length - 1
          ? current + 1
          : current
      );
    }, 450);

    analyze(datasetId)
      .then((result) => {
        setData(result);
      })
      .catch((err) => {
        setError(
          err instanceof Error
            ? err.message
            : 'Unable to analyze the dataset.'
        );
      })
      .finally(() => {
        setLoading(false);
        window.clearInterval(timer);
      });

    return () =>
      window.clearInterval(timer);
  }, [datasetId]);

  const askQ = async () => {
    const text = question.trim();

    if (!text || !datasetId || qLoading) {
      return;
    }

    setQLoading(true);
    setQError(null);
    setQResult(null);

    try {
      const result =
        await askQuestion(
          datasetId,
          text
        );

      setQResult(result);
    } catch (err) {
      setQError(
        err instanceof Error
          ? err.message
          : 'Unable to answer the question.'
      );
    } finally {
      setQLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold text-slate-800">
          Data Analysis
        </h1>

        <div className="bg-white rounded-xl border border-slate-200 p-8 flex flex-col items-center gap-3">
          <Loader2 className="w-7 h-7 text-blue-600 animate-spin" />
          <p className="text-slate-600 font-medium">
            {STEPS[step]}
          </p>
          <p className="text-xs text-slate-400">
            Processing locally with the DataPilot analysis engine
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold text-slate-800">
          Data Analysis
        </h1>

        <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 flex gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <div>
            <p className="font-semibold text-rose-800">
              Analysis failed
            </p>
            <p className="text-sm text-rose-700 mt-1">
              {error || 'No analysis result was returned.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      <div className="flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-blue-600" />
        <h1 className="text-xl font-bold text-slate-800">
          Autonomous Analyst
        </h1>

        <span className="ml-auto text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
          Deterministic Engine
        </span>
      </div>

      <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-6 text-white shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-100 mb-2">
          Analysis Summary
        </p>

        <p className="text-[15px] leading-relaxed">
          {data.summary}
        </p>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">
          Key Findings
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.key_findings.map(
            (finding) => (
              <div
                key={finding.id}
                className="bg-white rounded-xl border border-slate-200 p-4 flex gap-3"
              >
                <span className="text-blue-600 font-bold text-lg leading-none">
                  {String(
                    finding.id
                  ).padStart(2, '0')}
                </span>

                <p className="text-sm text-slate-700">
                  {finding.text}
                </p>
              </div>
            )
          )}
        </div>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">
          Numerical Statistics
        </h2>

        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden overflow-x-auto">
          {data.numeric_stats.length === 0 ? (
            <p className="p-8 text-sm text-slate-400 text-center">
              No numerical columns were detected.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  {[
                    'Column',
                    'Mean',
                    'Median',
                    'Min',
                    'Max',
                    'Std',
                    'IQR',
                    'Skew',
                  ].map((header) => (
                    <th
                      key={header}
                      className={`px-4 py-2.5 font-medium ${
                        header === 'Column'
                          ? 'text-left'
                          : 'text-right'
                      }`}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {data.numeric_stats.map(
                  (stat) => (
                    <tr
                      key={stat.column}
                      className="hover:bg-slate-50"
                    >
                      <td className="px-4 py-2.5 font-mono text-[13px] font-medium text-slate-800">
                        {stat.column}
                      </td>

                      <td className="px-4 py-2.5 text-right">{stat.mean}</td>
                      <td className="px-4 py-2.5 text-right">{stat.median}</td>
                      <td className="px-4 py-2.5 text-right">{stat.min}</td>
                      <td className="px-4 py-2.5 text-right">{stat.max}</td>
                      <td className="px-4 py-2.5 text-right">{stat.std}</td>
                      <td className="px-4 py-2.5 text-right">{stat.iqr}</td>
                      <td className="px-4 py-2.5 text-right">{stat.skewness}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {data.group_comparisons.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">
            Group Comparisons
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.group_comparisons
              .slice(0, 6)
              .map((comparison) => (
                <div
                  key={comparison.title}
                  className="bg-white rounded-xl border border-slate-200 overflow-hidden"
                >
                  <div className="px-4 py-2.5 border-b border-slate-100">
                    <p className="text-sm font-semibold text-slate-800">
                      {comparison.title}
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-slate-500 text-xs">
                        <tr>
                          <th className="text-left px-4 py-2">Category</th>
                          <th className="text-right px-4 py-2">Count</th>
                          <th className="text-right px-4 py-2">Mean</th>
                          <th className="text-right px-4 py-2">Median</th>
                        </tr>
                      </thead>

                      <tbody className="divide-y divide-slate-100">
                        {comparison.data
                          .slice(0, 8)
                          .map((row) => (
                            <tr
                              key={row.category}
                              className="hover:bg-slate-50"
                            >
                              <td className="px-4 py-2 text-slate-700">
                                {row.category}
                              </td>
                              <td className="px-4 py-2 text-right">
                                {row.count.toLocaleString()}
                              </td>
                              <td className="px-4 py-2 text-right font-medium">
                                {row.mean}
                              </td>
                              <td className="px-4 py-2 text-right">
                                {row.median}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {data.trends.available &&
        data.trends.trends &&
        data.trends.trends.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Trends ({data.trends.frequency})
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.trends.trends
                .slice(0, 4)
                .map((trend) => (
                  <div
                    key={trend.numeric_column}
                    className="bg-white rounded-xl border border-slate-200 p-4"
                  >
                    <p className="text-sm font-semibold text-slate-800">
                      {trend.numeric_column}
                    </p>

                    <p className="text-xs text-slate-500 mt-1">
                      Direction:{' '}
                      <span className="font-medium text-slate-700">
                        {trend.direction}
                      </span>
                      {' · '}
                      {trend.series.length} periods
                    </p>

                    <div className="flex items-end gap-0.5 h-20 mt-3">
                      {trend.series
                        .slice(-30)
                        .map((point, index) => {
                          const values =
                            trend.series
                              .map(
                                (item) =>
                                  item.value
                              )
                              .filter(
                                (
                                  value
                                ): value is number =>
                                  value !== null
                              );

                          const min =
                            Math.min(
                              ...values
                            );

                          const max =
                            Math.max(
                              ...values
                            );

                          const height =
                            max > min
                              ? (
                                  (point.value! - min) /
                                  (max - min)
                                ) * 100
                              : 50;

                          return (
                            <div
                              key={index}
                              className="flex-1 bg-blue-500 rounded-sm"
                              style={{
                                height: `${Math.max(
                                  4,
                                  height
                                )}%`,
                              }}
                              title={`${point.date}: ${point.value}`}
                            />
                          );
                        })}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <MessageCircle className="w-4 h-4" />
          Ask a Question
        </h2>

        <div className="bg-white rounded-xl border border-slate-200 p-4">

          <div className="flex gap-2">
            <input
              value={question}
              onChange={(event) =>
                setQuestion(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter'
                ) {
                  askQ();
                }
              }}
              placeholder="e.g. Which category has the highest average sales?"
              className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <button
              onClick={askQ}
              disabled={
                qLoading ||
                !question.trim()
              }
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5"
            >
              {qLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Ask
            </button>
          </div>

          {qError && (
            <div className="mt-3 p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700">
              {qError}
            </div>
          )}

          {qResult && (
            <div className="mt-4 space-y-4">

              <div className="p-4 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[11px] uppercase tracking-wide font-semibold text-slate-500">
                    {qResult.intent}
                  </span>

                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                    Local analysis
                  </span>
                </div>

                <p className="text-sm text-slate-800">
                  {qResult.answer}
                </p>
              </div>

              {qResult.visualizations &&
                qResult.visualizations.length > 0 && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {qResult.visualizations.map(
                      (chart, index) => (
                        <div
                          key={`${chart.title}-${index}`}
                          className="bg-white border border-slate-200 rounded-xl p-4"
                        >
                          <h3 className="text-sm font-semibold text-slate-800 mb-3">
                            {chart.title}
                          </h3>

                          <ChartRenderer
                            chart={chart}
                          />
                        </div>
                      )
                    )}
                  </div>
                )}

              {qResult.suggestions &&
                qResult.suggestions.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-500 mb-2">
                      Try another question
                    </p>

                    <div className="flex flex-wrap gap-1.5">
                      {qResult.suggestions.map(
                        (suggestion) => (
                          <button
                            key={suggestion}
                            onClick={() =>
                              setQuestion(
                                suggestion
                              )
                            }
                            className="text-xs px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-blue-50 hover:border-blue-300"
                          >
                            {suggestion}
                          </button>
                        )
                      )}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
