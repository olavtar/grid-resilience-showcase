{{/*
Common labels
*/}}
{{- define "dispatch-optimizer.labels" -}}
app.kubernetes.io/name: dispatch-optimizer
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "dispatch-optimizer.selectorLabels" -}}
app.kubernetes.io/name: dispatch-optimizer
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "dispatch-optimizer.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "dispatch-optimizer" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
