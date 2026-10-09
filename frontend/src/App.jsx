import React, { useState, useEffect, useRef } from 'react';
import TaskInput from './components/TaskInput';
import AgentTrace from './components/AgentTrace';
import PlanView from './components/PlanView';
import ApprovalModal from './components/ApprovalModal';
import VerificationResult from './components/VerificationResult';
import SummaryPanel from './components/SummaryPanel';
import { Bot } from 'lucide-react';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

export default function App() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('Idle'); // Idle, Planning, Running, Verifying, Done, Failed
  const [trace, setTrace] = useState([]);
  const [plan, setPlan] = useState(null);
  const [verification, setVerification] = useState(null);
  const [screenshots, setScreenshots] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [summary, setSummary] = useState(null);
  const wsRef = useRef(null);

  const handleSubmitTask = async (taskText) => {
    try {
      setIsRunning(true);
      setTaskId(null);
      setTrace([]);
      setPlan(null);
      setVerification(null);
      setScreenshots([]);
      setPendingQuestion(null);
      setSummary(null);
      setStatus('Planning');

      const res = await fetch(`${API_URL}/api/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: taskText })
      });
      const data = await res.json();
      setTaskId(data.task_id);
      connectWs(data.task_id);
    } catch (err) {
      console.error(err);
      setStatus('Failed');
      setIsRunning(false);
    }
  };

  const handleStopTask = async () => {
    if (!taskId) return;
    try {
      await fetch(`${API_URL}/api/task/${taskId}/stop`, {
        method: 'POST'
      });
      setIsRunning(false);
      setStatus('Failed');
    } catch (err) {
      console.error(err);
    }
  };

  const connectWs = (id) => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(`${WS_URL}/ws/${id}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      const d = msg.data || {};
      switch (msg.type) {
        case 'status':
          setStatus(d.status || 'running');
          break;
        case 'plan_created':
          setPlan(d.plan);
          break;
        case 'step_started':
          setTrace(prev => [...prev, {
            id: d.iteration,
            tool: d.tool,
            args: d.args,
            reasoning: d.reasoning,
            status: 'running'
          }]);
          break;
        case 'step_completed':
          setTrace(prev => prev.map(s =>
            s.id === d.iteration
              ? { ...s, result: d.result, success: d.success, screenshot: d.screenshot, status: d.success ? 'done' : 'failed' }
              : s
          ));
          if (d.screenshot) {
            setScreenshots(prev => [...prev, d.screenshot]);
          }
          break;
        case 'human_request':
          setPendingQuestion({ question: d.question, context: d.context });
          break;
        case 'verification_done':
          setVerification(d.verification);
          break;
        case 'task_complete':
          setStatus('done');
          setIsRunning(false);
          setSummary(d.summary);
          if (d.screenshots) setScreenshots(d.screenshots);
          break;
        case 'state':
          // Initial state sync
          if (d.status) setStatus(d.status);
          if (d.trace) setTrace(d.trace);
          if (d.plan) setPlan(d.plan);
          if (d.verification) setVerification(d.verification);
          if (d.final_summary) setSummary(d.final_summary);
          break;
        case 'error':
          setStatus('failed');
          setIsRunning(false);
          break;
        default:
          break;
      }
    };
  };

  const handleAnswer = async (answer) => {
    if (!taskId) return;
    try {
      await fetch(`${API_URL}/api/task/${taskId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer })
      });
      setPendingQuestion(null);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f1117] text-white flex flex-col font-sans">
      <header className="border-b border-[#2a2d3e] bg-[#161b27] p-4 flex items-center shadow-sm z-10">
        <div className="flex items-center gap-3">
          <div className="bg-purple-600 p-2 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Autonomous AI Worker</h1>
            <p className="text-xs text-[#8892a4]">AI Engineering Demo Interface</p>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        <div className="w-full lg:w-1/3 flex flex-col border-r border-[#2a2d3e] bg-[#12141c] overflow-y-auto">
          <div className="p-4 flex flex-col gap-6">
            <TaskInput onSubmit={handleSubmitTask} onStop={handleStopTask} isRunning={isRunning} status={status} />
            {plan && <PlanView plan={plan} currentTrace={trace} status={status} />}
            {verification && <VerificationResult result={verification} />}
            {summary && <SummaryPanel summary={summary} screenshots={screenshots} taskId={taskId} API_URL={API_URL} onReset={() => setStatus('Idle')} />}
          </div>
        </div>

        <div className="w-full lg:w-2/3 flex flex-col bg-[#0f1117] overflow-y-auto relative p-4">
          <AgentTrace trace={trace} taskId={taskId} API_URL={API_URL} />
        </div>

        {pendingQuestion && (
          <ApprovalModal question={pendingQuestion} onSubmit={handleAnswer} />
        )}
      </main>
    </div>
  );
}
