import { createBrowserRouter, Navigate } from 'react-router-dom';
import { OpsShell } from '../components/layout/OpsShell';
import { RequireRole } from '../components/common/RequireRole';
import { LoginPage } from '../pages/Login';
import { SourcesPage } from '../pages/Sources';
import { PipelinesPage } from '../pages/Pipelines';
import { MappingEditorPage } from '../pages/MappingEditor';
import { RunsPage } from '../pages/Runs';
import { RunDetailPage } from '../pages/RunDetail';
import { TargetsPage } from '../pages/Targets';
import { requireAuth } from './guards';

const shell = (element: React.ReactNode) => (
  <OpsShell>{element}</OpsShell>
);

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    loader: requireAuth,
    element: <Navigate to="/sources" replace />,
  },
  {
    path: '/sources',
    loader: requireAuth,
    element: shell(<SourcesPage />),
  },
  {
    path: '/pipelines',
    loader: requireAuth,
    element: shell(<PipelinesPage />),
  },
  {
    path: '/pipelines/:id/mapping',
    loader: requireAuth,
    element: shell(
      <RequireRole roles={['owner', 'operator']} message="viewer（BI）只读，不能访问映射编辑器。">
        <MappingEditorPage />
      </RequireRole>,
    ),
  },
  {
    path: '/runs',
    loader: requireAuth,
    element: shell(<RunsPage />),
  },
  {
    path: '/runs/:id',
    loader: requireAuth,
    element: shell(<RunDetailPage />),
  },
  {
    path: '/targets',
    loader: requireAuth,
    element: shell(<TargetsPage />),
  },
  { path: '*', element: <Navigate to="/sources" replace /> },
]);
