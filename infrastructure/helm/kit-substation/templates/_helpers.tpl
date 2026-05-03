{{/*
Common labels
*/}}
{{- define "kit-substation.labels" -}}
app.kubernetes.io/name: kit-substation
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Namespace helper
*/}}
{{- define "kit-substation.namespace" -}}
{{- .Values.namespace | default .Release.Namespace }}
{{- end }}
