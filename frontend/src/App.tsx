/**
 * App.tsx — root component with a minimal view state machine.
 *
 * Views:
 *   'home'   → HomeScreen  (file selection + search)
 *   'review' → ReviewScreen (loading → result/error)
 *
 * The upload pipeline (useUpload) lives here so state persists across
 * the view transition — HomeScreen fires upload.upload(), the view
 * immediately switches to 'review', and ReviewScreen watches upload.phase.
 */
import { useState, useCallback } from 'react';
import './App.css';
import HomeScreen   from './screens/HomeScreen';
import ReviewScreen from './screens/ReviewScreen';
import { useUpload } from './hooks/useUpload';

type View = 'home' | 'review';

export default function App() {
  const [view, setView]  = useState<View>('home');
  const upload           = useUpload();

  const handleFileSelect = useCallback(
    (file: File) => {
      upload.reset();        // clear any previous run
      setView('review');     // show review immediately (loading state)
      upload.upload(file);   // fire-and-forget; ReviewScreen watches phase
    },
    [upload],
  );

  const handleBack = useCallback(() => {
    upload.reset();
    setView('home');
  }, [upload]);

  return (
    <>
      {view === 'home' && (
        <HomeScreen onFileSelect={handleFileSelect} />
      )}
      {view === 'review' && (
        <ReviewScreen upload={upload} onBack={handleBack} />
      )}
    </>
  );
}
