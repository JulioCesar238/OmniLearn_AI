import React, { useState, useCallback, useEffect } from 'react';
import { AppState, AppStep, Difficulty, Quiz, Course, LessonImage } from './types';
import * as gemini from './services/geminiService';
import { Loading } from './components/Loading';
import { Button } from './components/Button';
import { MarkdownView } from './components/MarkdownView';

// --- Icons (SVG) ---
const BookIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
);
const GradCapIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>
);
const ArrowLeftIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 19-7-7 7-7 7-7"/><path d="M19 12H5"/></svg>
);
const ArrowRightIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
);
const PlusIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
);
const TrashIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
);
const SpeakerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
);
const StopCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><rect x="9" y="9" width="6" height="6"></rect></svg>
);

// --- Components ---

const ScrollProgress = () => {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPosition = window.scrollY;
      
      if (totalHeight <= 0) {
          setWidth(100);
          return;
      }
      
      const percent = (scrollPosition / totalHeight) * 100;
      setWidth(Math.min(100, Math.max(0, percent)));
    };

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', handleScroll);
    handleScroll();
    
    return () => {
        window.removeEventListener('scroll', handleScroll);
        window.removeEventListener('resize', handleScroll);
    };
  }, []);

  return (
    <div className="fixed top-16 left-0 w-full h-1 bg-slate-100 z-40">
      <div 
        className="h-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.4)] transition-all duration-100 ease-out" 
        style={{ width: `${width}%` }}
      />
    </div>
  );
};

// --- Helpers ---

const cleanMarkdownForSpeech = (markdown: string): string => {
  return markdown
    .replace(/[#*`_]/g, '') // Remove common markdown symbols
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '') // Remove images
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Keep link text, remove url
    .replace(/---/g, '') // Remove horizontal rules
    .replace(/\n+/g, '. '); // Replace newlines with natural pauses
};

export default function App() {
  // --- State Initialization ---
  const [state, setState] = useState<AppState>(() => {
    // Load from local storage on initial render
    const savedCoursesStr = localStorage.getItem('omniLearnCourses');
    let savedCourses: Course[] = [];
    if (savedCoursesStr) {
      try {
        const parsed = JSON.parse(savedCoursesStr);
        // Migration: Ensure imageCache is valid (it used to be string, now it's LessonImage object)
        // If it was a string (old AI image), we discard it to force fetching a new "Internet" image.
        savedCourses = parsed.map((c: any) => {
            const cleanImageCache: Record<string, LessonImage> = {};
            if (c.imageCache) {
                Object.keys(c.imageCache).forEach(key => {
                    const val = c.imageCache[key];
                    // Only keep if it looks like our new LessonImage object
                    if (typeof val === 'object' && val.url && val.sourceUrl) {
                        cleanImageCache[key] = val;
                    }
                });
            }

            return {
                ...c,
                imageCache: cleanImageCache,
                subtopicCount: c.subtopicCount || 10,
                lessonCount: c.lessonCount || 10
            };
        });
      } catch (e) {
        console.error("Failed to parse courses", e);
      }
    }

    return {
        step: AppStep.DASHBOARD,
        courses: savedCourses,
        activeCourseId: null,
        selectedSubtopic: null,
        selectedLesson: null,
        currentQuiz: null,
        isLoading: false,
        loadingMessage: '',
        error: null,
    };
  });

  const [inputTopic, setInputTopic] = useState('');
  const [inputDifficulty, setInputDifficulty] = useState<Difficulty>(Difficulty.BASIC);
  const [inputSubtopicCount, setInputSubtopicCount] = useState<number>(10);
  const [inputLessonCount, setInputLessonCount] = useState<number>(10);
  
  const [isSpeaking, setIsSpeaking] = useState(false);

  const [quizState, setQuizState] = useState<{
    selectedAnswers: Record<number, string>;
    submitted: boolean;
    score: number;
  }>({ selectedAnswers: {}, submitted: false, score: 0 });

  // --- Effects ---

  // Persist courses whenever they change
  useEffect(() => {
    localStorage.setItem('omniLearnCourses', JSON.stringify(state.courses));
  }, [state.courses]);

  // Clean up speech when navigating away from content or changing lessons
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsSpeaking(false);
    };
  }, [state.step, state.selectedLesson]);

  // --- Helpers ---

  const getActiveCourse = useCallback(() => {
    return state.courses.find(c => c.id === state.activeCourseId);
  }, [state.courses, state.activeCourseId]);

  const updateActiveCourse = (updater: (course: Course) => Course) => {
    setState(prev => ({
        ...prev,
        courses: prev.courses.map(c => c.id === prev.activeCourseId ? updater(c) : c)
    }));
  };

  const handleToggleSpeech = (content: string) => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      const textToSpeak = cleanMarkdownForSpeech(content);
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.lang = 'es-ES'; // Spanish locale
      utterance.rate = 1.0;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
      setIsSpeaking(true);
    }
  };

  // --- Action Handlers ---

  const handleCreateCourse = async () => {
    if (!inputTopic.trim()) return;
    
    // Validate inputs
    const subtopicsToGen = Math.min(Math.max(inputSubtopicCount, 1), 20); // Clamp between 1 and 20
    const lessonsToGen = Math.min(Math.max(inputLessonCount, 1), 20); // Clamp between 1 and 20

    const newCourseId = Date.now().toString();
    const newCourse: Course = {
        id: newCourseId,
        topic: inputTopic,
        difficulty: inputDifficulty,
        subtopicCount: subtopicsToGen,
        lessonCount: lessonsToGen,
        createdAt: Date.now(),
        subtopics: [],
        lessonsCache: {},
        contentCache: {},
        imageCache: {},
        completedQuizzes: {}
    };

    setState(prev => ({ 
        ...prev, 
        isLoading: true, 
        loadingMessage: "Generando plan de estudios...",
        error: null 
    }));

    try {
      // Pre-fetch subtopics immediately
      const subtopics = await gemini.generateSubtopics(inputTopic, inputDifficulty, subtopicsToGen);
      newCourse.subtopics = subtopics;

      setState(prev => ({
        ...prev,
        courses: [...prev.courses, newCourse],
        activeCourseId: newCourseId,
        step: AppStep.SUBTOPICS,
        isLoading: false,
        selectedSubtopic: null
      }));
      setInputTopic(''); // Clear input
      setInputSubtopicCount(10); // Reset defaults
      setInputLessonCount(10);
    } catch (err) {
      console.error(err);
      setState(prev => ({ ...prev, isLoading: false, error: "Error al generar subtemas. Intenta de nuevo." }));
    }
  };

  const handleResumeCourse = (courseId: string) => {
      setState(prev => ({
          ...prev,
          activeCourseId: courseId,
          step: AppStep.SUBTOPICS,
          selectedSubtopic: null,
          selectedLesson: null,
          error: null
      }));
  };

  const handleDeleteCourse = (courseId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      if(window.confirm("¿Estás seguro de que quieres eliminar este curso?")) {
        setState(prev => ({
            ...prev,
            courses: prev.courses.filter(c => c.id !== courseId),
            activeCourseId: prev.activeCourseId === courseId ? null : prev.activeCourseId,
            step: prev.activeCourseId === courseId ? AppStep.DASHBOARD : prev.step
        }));
      }
  };

  const handleSelectSubtopic = async (subtopic: string) => {
    const course = getActiveCourse();
    if (!course) return;

    setState(prev => ({ ...prev, selectedSubtopic: subtopic }));

    // Check cache first
    if (course.lessonsCache[subtopic] && course.lessonsCache[subtopic].length > 0) {
        setState(prev => ({ ...prev, step: AppStep.LESSONS }));
        return;
    }

    setState(prev => ({ ...prev, isLoading: true, loadingMessage: "Generando lecciones..." }));
    
    try {
      // Use the course's configured lesson count, default to 10 if missing (backward compatibility)
      const count = course.lessonCount || 10;
      const lessons = await gemini.generateLessons(course.topic, subtopic, course.difficulty, count);
      updateActiveCourse(c => ({
          ...c,
          lessonsCache: { ...c.lessonsCache, [subtopic]: lessons }
      }));
      setState(prev => ({ ...prev, step: AppStep.LESSONS, isLoading: false }));
    } catch (err) {
      console.error(err);
      setState(prev => ({ ...prev, isLoading: false, error: "Error al generar lecciones." }));
    }
  };

  const handleSelectLesson = useCallback(async (lesson: string) => {
    // Note: We need to use functional state updates or Refs if we want to access latest state 
    // inside a callback if it wasn't refreshed, but here we rebuild the closure when deps change.
    // However, for handleSelectLesson to be used in other callbacks, we need to be careful.
    
    // We get the active course from the latest state inside the setter if needed, 
    // but complex async logic is easier with the 'state' in scope if we trust deps.
    
    // To fix dependency chain for navigateToLesson, we'll access state directly from the closure scope
    // and ensure handleSelectLesson is stable or re-created correctly.
    
    // Actually, accessing `state` directly here works because `handleSelectLesson`
    // will be recreated whenever `state` changes if we list it in deps, 
    // OR we just use the functions without useCallback for simple handlers.
    // But for navigateToLesson (used in effect), we need stability.

    // Let's rely on the outer `state` variable which is fresh on every render.
    
    const course = state.courses.find(c => c.id === state.activeCourseId);
    if (!course || !state.selectedSubtopic) return;

    setState(prev => ({ ...prev, selectedLesson: lesson }));

    // Check content cache
    const hasContent = !!course.contentCache[lesson];
    const hasImage = !!course.imageCache[lesson];

    if (hasContent && hasImage) {
        setState(prev => ({ ...prev, step: AppStep.CONTENT }));
        return;
    }

    setState(prev => ({ ...prev, isLoading: true, loadingMessage: "Preparando material didáctico e ilustraciones..." }));
    
    try {
      // Fetch text content if missing
      let content = course.contentCache[lesson];
      if (!content) {
        content = await gemini.generateLessonContent(course.topic, state.selectedSubtopic, lesson, course.difficulty);
      }

      // Fetch image if missing (fire and await to show everything at once for better impact, though it adds a few seconds)
      let imageObj = course.imageCache[lesson];
      if (!imageObj) {
        const foundImage = await gemini.getLessonImage(course.topic, lesson);
        if (foundImage) imageObj = foundImage;
      }

      updateActiveCourse(c => ({
          ...c,
          contentCache: { ...c.contentCache, [lesson]: content },
          imageCache: imageObj ? { ...c.imageCache, [lesson]: imageObj } : c.imageCache
      }));

      setState(prev => ({ ...prev, step: AppStep.CONTENT, isLoading: false }));
    } catch (err) {
        console.error(err);
        setState(prev => ({ ...prev, isLoading: false, error: "Error al generar contenido." }));
    }
  }, [state.courses, state.activeCourseId, state.selectedSubtopic]);

  const handleStartQuiz = async () => {
    const course = getActiveCourse();
    if (!course || !state.selectedLesson) return;
    
    const content = course.contentCache[state.selectedLesson];
    if (!content) return;

    setState(prev => ({ ...prev, isLoading: true, loadingMessage: "Diseñando evaluación..." }));
    try {
      const quiz = await gemini.generateQuiz(content);
      setState(prev => ({
        ...prev,
        currentQuiz: quiz,
        step: AppStep.QUIZ,
        isLoading: false
      }));
      setQuizState({ selectedAnswers: {}, submitted: false, score: 0 });
    } catch (err) {
      console.error(err);
      setState(prev => ({ ...prev, isLoading: false, error: "Error al generar el cuestionario." }));
    }
  };

  const handleQuizSubmit = () => {
    if (!state.currentQuiz || !state.selectedLesson) return;
    
    let score = 0;
    state.currentQuiz.questions.forEach(q => {
      if (quizState.selectedAnswers[q.id] === q.correctOptionId) {
        score++;
      }
    });

    // Save score
    updateActiveCourse(c => ({
        ...c,
        completedQuizzes: { ...c.completedQuizzes, [state.selectedLesson!]: score }
    }));

    setQuizState(prev => ({ ...prev, submitted: true, score }));
  };

  // --- Navigation Logic ---

  const goToDashboard = () => {
      setState(prev => ({ 
          ...prev, 
          step: AppStep.DASHBOARD, 
          activeCourseId: null,
          selectedSubtopic: null,
          selectedLesson: null
      }));
  };

  const goBack = () => {
    setState(prev => {
        switch (prev.step) {
            case AppStep.INPUT: return { ...prev, step: AppStep.DASHBOARD };
            case AppStep.SUBTOPICS: return { ...prev, step: AppStep.DASHBOARD, activeCourseId: null }; // Exit course
            case AppStep.LESSONS: return { ...prev, step: AppStep.SUBTOPICS };
            case AppStep.CONTENT: return { ...prev, step: AppStep.LESSONS };
            case AppStep.QUIZ: return { ...prev, step: AppStep.CONTENT };
            default: return prev;
        }
    });
  };

  const navigateToLesson = useCallback((direction: 'next' | 'prev') => {
      const course = state.courses.find(c => c.id === state.activeCourseId);
      if(!course || !state.selectedSubtopic || !state.selectedLesson) return;

      const currentLessons = course.lessonsCache[state.selectedSubtopic] || [];
      const currentIndex = currentLessons.indexOf(state.selectedLesson);

      if (direction === 'next' && currentIndex < currentLessons.length - 1) {
          handleSelectLesson(currentLessons[currentIndex + 1]);
      } else if (direction === 'prev' && currentIndex > 0) {
          handleSelectLesson(currentLessons[currentIndex - 1]);
      }
  }, [state.courses, state.activeCourseId, state.selectedSubtopic, state.selectedLesson, handleSelectLesson]);

  // Keyboard Navigation Effect
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
        if (state.step !== AppStep.CONTENT || state.isLoading) return;

        if (e.key === 'ArrowLeft') {
            navigateToLesson('prev');
        } else if (e.key === 'ArrowRight') {
            navigateToLesson('next');
        }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
        window.removeEventListener('keydown', handleKeyDown);
    };
  }, [state.step, state.isLoading, navigateToLesson]);


  // --- Render Components ---

  const renderDashboard = () => (
      <div className="max-w-4xl mx-auto space-y-8">
          <div className="flex justify-between items-end border-b border-slate-200 pb-6">
              <div>
                <h2 className="text-3xl font-bold text-slate-800">Mis Cursos</h2>
                <p className="text-slate-500 mt-1">Gestiona tu aprendizaje y progreso</p>
              </div>
              <Button onClick={() => setState(prev => ({ ...prev, step: AppStep.INPUT }))} className="flex items-center gap-2">
                  <PlusIcon /> Nuevo Curso
              </Button>
          </div>

          {state.courses.length === 0 ? (
              <div className="text-center py-16 bg-white rounded-xl border border-dashed border-slate-300">
                  <div className="bg-blue-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 text-blue-500">
                      <BookIcon />
                  </div>
                  <h3 className="text-lg font-medium text-slate-900">Bienvenido a OmniLearn AI</h3>
                  <p className="text-slate-500 mb-6">
                    Genera cursos estructurados sobre cualquier tema al instante.
                    <br />
                    Comienza creando tu primer plan de estudios.
                  </p>
                  <Button onClick={() => setState(prev => ({ ...prev, step: AppStep.INPUT }))}>
                      Crear Curso
                  </Button>
              </div>
          ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {state.courses.map(course => {
                      const completedCount = Object.keys(course.completedQuizzes).length;
                      // Calculate progress based on dynamic counts, default to 10x10 if missing
                      const totalLessons = (course.subtopicCount || 10) * (course.lessonCount || 10);
                      const progressPercent = Math.min(100, Math.round((completedCount / totalLessons) * 100));

                      return (
                          <div key={course.id} onClick={() => handleResumeCourse(course.id)} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 cursor-pointer hover:shadow-md hover:border-blue-400 transition-all group relative">
                              <button 
                                onClick={(e) => handleDeleteCourse(course.id, e)}
                                className="absolute top-4 right-4 text-slate-400 hover:text-red-500 transition-colors p-1"
                                title="Eliminar curso"
                              >
                                  <TrashIcon />
                              </button>
                              
                              <h3 className="text-xl font-bold text-slate-800 mb-1 group-hover:text-blue-700 truncate pr-8">{course.topic}</h3>
                              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-4 ${
                                  course.difficulty === Difficulty.BASIC ? 'bg-green-100 text-green-700' :
                                  course.difficulty === Difficulty.MEDIUM ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-red-100 text-red-700'
                              }`}>
                                  {course.difficulty}
                              </span>

                              <div className="space-y-2">
                                  <div className="flex justify-between text-sm text-slate-600">
                                      <span>Progreso General</span>
                                      <span className="font-semibold">{progressPercent}%</span>
                                  </div>
                                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                                      <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${progressPercent}%` }}></div>
                                  </div>
                                  <p className="text-xs text-slate-400 mt-2">
                                      {completedCount} de {totalLessons} lecciones completadas
                                  </p>
                              </div>
                          </div>
                      );
                  })}
              </div>
          )}
      </div>
  );

  const renderInput = () => (
    <div className="max-w-xl mx-auto bg-white p-8 rounded-2xl shadow-xl border border-slate-100 relative">
      <button 
        onClick={() => setState(prev => ({ ...prev, step: AppStep.DASHBOARD }))}
        className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
      >
          <span className="text-2xl">&times;</span>
      </button>

      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-slate-800 mb-2">Nuevo Tema</h2>
        <p className="text-slate-500">Personaliza la estructura de tu curso.</p>
      </div>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">¿Qué quieres aprender?</label>
          <input
            type="text"
            value={inputTopic}
            onChange={(e) => setInputTopic(e.target.value)}
            placeholder="Ej. Física Cuántica, Historia del Arte, Python..."
            className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Nivel de Dificultad</label>
          <div className="grid grid-cols-3 gap-3">
            {Object.values(Difficulty).map((level) => (
              <button
                key={level}
                onClick={() => setInputDifficulty(level)}
                className={`py-3 px-2 rounded-lg text-sm font-medium border transition-all ${
                  inputDifficulty === level 
                    ? 'bg-blue-50 border-blue-500 text-blue-700 ring-1 ring-blue-500' 
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Número de Subtemas</label>
                <input
                    type="number"
                    min="1"
                    max="20"
                    value={inputSubtopicCount}
                    onChange={(e) => setInputSubtopicCount(parseInt(e.target.value) || 10)}
                    className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                />
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Lecciones por Subtema</label>
                <input
                    type="number"
                    min="1"
                    max="20"
                    value={inputLessonCount}
                    onChange={(e) => setInputLessonCount(parseInt(e.target.value) || 10)}
                    className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                />
            </div>
        </div>

        <Button 
            className="w-full py-3 text-lg mt-4" 
            onClick={handleCreateCourse} 
            disabled={!inputTopic}
        >
          Generar Curso
        </Button>
      </div>
    </div>
  );

  const renderList = (items: string[], onSelect: (item: string) => void, title: string, subtitle: string, type: 'subtopic' | 'lesson') => {
      const course = getActiveCourse();
      return (
        <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
            <div>
                <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
                <p className="text-slate-500">{subtitle}</p>
            </div>
            <Button variant="outline" onClick={goBack} className="flex items-center gap-2 px-3">
                <ArrowLeftIcon /> {type === 'lesson' ? 'Volver al Curso' : 'Volver'}
            </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {items.map((item, idx) => {
                // Determine status for styling
                let statusColor = "bg-blue-100 text-blue-600"; // Default
                let statusBorder = "border-slate-200";
                let statusIcon = idx + 1;
                
                if (type === 'lesson' && course) {
                    const score = course.completedQuizzes[item];
                    if (score !== undefined) {
                        statusColor = score >= 3 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700";
                        statusBorder = score >= 3 ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50";
                    }
                }

                return (
                    <div 
                        key={idx}
                        onClick={() => onSelect(item)}
                        className={`p-5 rounded-xl shadow-sm border ${statusBorder} bg-white hover:shadow-md hover:border-blue-400 hover:scale-[1.01] transition-all cursor-pointer group`}
                    >
                        <div className="flex items-start gap-4">
                        <span className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm shrink-0 mt-0.5 ${statusColor}`}>
                            {statusIcon}
                        </span>
                        <div className="flex-grow">
                            <h3 className="text-lg font-medium text-slate-800 group-hover:text-blue-700">{item}</h3>
                            {type === 'lesson' && course && course.completedQuizzes[item] !== undefined && (
                                <span className={`text-xs font-bold ${course.completedQuizzes[item] >= 3 ? "text-green-600" : "text-red-600"}`}>
                                    Nota: {course.completedQuizzes[item]}/5
                                </span>
                            )}
                        </div>
                        </div>
                    </div>
                );
            })}
        </div>
        </div>
      );
    };

  const renderContent = () => {
    const course = getActiveCourse();
    if (!course || !state.selectedSubtopic || !state.selectedLesson) return null;

    const currentLessons = course.lessonsCache[state.selectedSubtopic] || [];
    const currentIndex = currentLessons.indexOf(state.selectedLesson);
    const hasNext = currentIndex < currentLessons.length - 1;
    const hasPrev = currentIndex > 0;
    const imageObj = course.imageCache[state.selectedLesson];
    const contentText = course.contentCache[state.selectedLesson] || "";

    return (
        <div className="max-w-3xl mx-auto flex flex-col min-h-[70vh]">
            <ScrollProgress />
            <div className="bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden flex flex-col flex-grow">
                <div className="bg-slate-50 p-4 border-b flex justify-between items-center sticky top-0 z-10">
                    <Button variant="outline" onClick={goBack} className="flex items-center gap-2 text-sm py-1 px-3">
                        <ArrowLeftIcon /> Lista
                    </Button>
                    <div className="text-center">
                        <div className="text-xs text-slate-500 uppercase tracking-wide">Lección {currentIndex + 1} de {currentLessons.length}</div>
                        <span className="font-semibold text-slate-700 text-sm truncate block max-w-[200px] md:max-w-md">{state.selectedLesson}</span>
                    </div>
                    <div className="w-20 flex justify-end">
                       <Button 
                          variant="outline"
                          onClick={() => handleToggleSpeech(contentText)}
                          className={`p-2 rounded-full border ${isSpeaking ? 'border-red-400 text-red-600 bg-red-50' : 'border-slate-300 text-slate-600'}`}
                          title={isSpeaking ? "Detener narración" : "Escuchar lección"}
                       >
                         {isSpeaking ? <StopCircleIcon /> : <SpeakerIcon />}
                       </Button>
                    </div>
                </div>
                
                <div className="p-8 md:p-12 flex-grow">
                    {imageObj && (
                        <figure className="mb-10 text-center">
                            <div className="rounded-xl overflow-hidden shadow-md border border-slate-100 inline-block max-w-full">
                                <img 
                                  src={imageObj.url} 
                                  alt={imageObj.title} 
                                  className="w-full h-auto object-cover max-h-[400px]" 
                                  onError={(e) => (e.currentTarget.style.display = 'none')}
                                />
                            </div>
                            <figcaption className="text-xs text-slate-500 mt-2 font-light">
                                <em>{imageObj.title}</em>. [Imagen]. {imageObj.author}. Recuperado de <a href={imageObj.sourceUrl} target="_blank" rel="noreferrer" className="underline hover:text-slate-800">Wikimedia Commons</a>. {imageObj.license}.
                            </figcaption>
                        </figure>
                    )}
                    <MarkdownView content={contentText} />
                </div>

                <div className="p-4 bg-slate-50 border-t sticky bottom-0 z-10 flex justify-between items-center gap-4">
                     <Button 
                        variant="outline" 
                        onClick={() => navigateToLesson('prev')} 
                        disabled={!hasPrev}
                        className={`flex items-center gap-2 ${!hasPrev ? "invisible" : ""}`}
                        title="Anterior (Flecha Izquierda)"
                    >
                        <ArrowLeftIcon /> Anterior 
                        <span className="hidden md:inline-block ml-1 text-[10px] text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded font-mono">[←]</span>
                    </Button>

                    <Button onClick={handleStartQuiz} className="flex items-center gap-2 shadow-lg ring-2 ring-white">
                        <GradCapIcon /> Evaluar Conocimiento
                    </Button>

                    <Button 
                        variant="outline" 
                        onClick={() => navigateToLesson('next')} 
                        disabled={!hasNext}
                        className={`flex items-center gap-2 ${!hasNext ? "invisible" : ""}`}
                        title="Siguiente (Flecha Derecha)"
                    >
                        Siguiente <span className="hidden md:inline-block ml-1 text-[10px] text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded font-mono">[→]</span> <ArrowRightIcon />
                    </Button>
                </div>
            </div>
        </div>
    );
  };

  const renderQuiz = () => {
    if (!state.currentQuiz) return null;

    return (
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
        <div className="bg-slate-900 text-white p-6 flex justify-between items-center">
            <div>
                <h2 className="text-xl font-bold flex items-center gap-2">
                    <GradCapIcon /> Cuestionario
                </h2>
                <p className="text-slate-400 text-sm mt-1">{state.selectedLesson}</p>
            </div>
        </div>
        
        <div className="p-8 space-y-8">
          {state.currentQuiz.questions.map((q) => {
            return (
              <div key={q.id} className="space-y-4">
                <p className="font-semibold text-lg text-slate-800">
                  <span className="text-slate-400 mr-2">{q.id}.</span>
                  {q.statement}
                </p>
                <div className="space-y-2 pl-6">
                  {q.options.map((opt) => {
                    let optionClass = "border-slate-200 hover:bg-slate-50";
                    if (quizState.submitted) {
                      if (opt.id === q.correctOptionId) optionClass = "bg-green-100 border-green-500 text-green-800";
                      else if (quizState.selectedAnswers[q.id] === opt.id) optionClass = "bg-red-100 border-red-500 text-red-800";
                      else optionClass = "opacity-50";
                    } else if (quizState.selectedAnswers[q.id] === opt.id) {
                      optionClass = "bg-blue-50 border-blue-500 text-blue-800 ring-1 ring-blue-500";
                    }

                    return (
                      <div 
                        key={opt.id}
                        onClick={() => !quizState.submitted && setQuizState(prev => ({
                          ...prev, 
                          selectedAnswers: { ...prev.selectedAnswers, [q.id]: opt.id }
                        }))}
                        className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center gap-3 ${optionClass}`}
                      >
                        <div className={`w-6 h-6 rounded-full border flex items-center justify-center text-xs font-bold ${
                            quizState.selectedAnswers[q.id] === opt.id || (quizState.submitted && opt.id === q.correctOptionId) ? 'bg-white border-current' : 'bg-slate-100 text-slate-500'
                        }`}>
                            {opt.id}
                        </div>
                        <span>{opt.text}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-6 bg-slate-50 border-t flex justify-between items-center">
            {quizState.submitted ? (
                 <div className="flex items-center gap-4">
                    <div className="text-lg font-bold">
                        Puntuación: <span className={quizState.score >= 3 ? "text-green-600" : "text-red-600"}>{quizState.score} / 5</span>
                    </div>
                 </div>
            ) : (
                <div className="text-sm text-slate-500">
                    Responde todo para calificar
                </div>
            )}
            
            {quizState.submitted ? (
                <div className="flex gap-2">
                    <Button onClick={goBack} variant="outline">Repasar Lección</Button>
                    <Button onClick={() => setState(prev => ({ ...prev, step: AppStep.LESSONS }))} variant="primary">
                        Siguiente Lección
                    </Button>
                </div>
            ) : (
                <Button 
                    onClick={handleQuizSubmit} 
                    disabled={Object.keys(quizState.selectedAnswers).length < 5}
                >
                    Calificar
                </Button>
            )}
        </div>
      </div>
    );
  };

  // --- Main Layout ---

  const activeCourse = getActiveCourse();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={goToDashboard}>
            <div className="bg-blue-600 text-white p-1.5 rounded-lg">
                <BookIcon />
            </div>
            <div>
                <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-blue-500">
                OmniLearn AI
                </h1>
                <p className="text-[10px] text-slate-400 font-medium -mt-1 tracking-wide">By Julio Cesar Montoya Rendón</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {activeCourse && (
                <div className="hidden md:flex flex-col items-end mr-2">
                    <span className="text-sm font-bold text-slate-800">{activeCourse.topic}</span>
                    <span className="text-xs text-slate-500">{activeCourse.difficulty}</span>
                </div>
            )}
            {state.step !== AppStep.DASHBOARD && (
                <Button variant="outline" className="text-sm py-1.5" onClick={goToDashboard}>
                    Mis Cursos
                </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow p-4 md:p-8">
        {state.error && (
            <div className="max-w-xl mx-auto mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-center shadow-sm">
                {state.error}
            </div>
        )}

        {state.isLoading ? (
          <Loading message={state.loadingMessage || "Cargando..."} />
        ) : (
          <>
            {state.step === AppStep.DASHBOARD && renderDashboard()}
            
            {state.step === AppStep.INPUT && renderInput()}
            
            {state.step === AppStep.SUBTOPICS && activeCourse && renderList(
              activeCourse.subtopics, 
              handleSelectSubtopic, 
              `Plan de Estudios: ${activeCourse.topic}`,
              "Selecciona un subtema para profundizar.",
              'subtopic'
            )}
            
            {state.step === AppStep.LESSONS && activeCourse && state.selectedSubtopic && renderList(
              activeCourse.lessonsCache[state.selectedSubtopic] || [], 
              handleSelectLesson, 
              `Lecciones: ${state.selectedSubtopic}`,
              "Selecciona una lección para comenzar.",
              'lesson'
            )}
            
            {state.step === AppStep.CONTENT && renderContent()}
            
            {state.step === AppStep.QUIZ && renderQuiz()}
          </>
        )}
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-4 text-center text-slate-400 text-sm">
          <p>© {new Date().getFullYear()} OmniLearn AI. Desarrollado por <strong>Julio Cesar Montoya Rendón</strong>. Powered by Google Gemini.</p>
        </div>
      </footer>
    </div>
  );
}

