export type SubjectType =
  | "fop_resident"
  | "legal_resident"
  | "non_resident"
  | "individual";

export type LoginFormState = {
  email: string;
  password: string;
};

export type LoginFormErrors = {
  email: string;
  password: string;
  form: string;
};

export type RegisterStep1FormState = {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  password: string;
};

export type RegisterStep1Errors = {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  password: string;
  form: string;
};

export type RegisterStep2FormState = {
  subject_type: SubjectType;
  edrpou: string;
  name: string;
  registration_country: string;
  company_address: string;
  identity_document: File | null;
  agree_trade_rules: boolean;
  agree_privacy_policy: boolean;
};

export type RegisterStep2Errors = {
  subject_type: string;
  edrpou: string;
  name: string;
  registration_country: string;
  company_address: string;
  identity_document: string;
  agree_trade_rules: string;
  agree_privacy_policy: string;
  form: string;
};

export type RegisterStep3FormState = {
  goal_tenders: boolean;
  goal_participation: boolean;
  agree_participation_visibility: boolean;
};

export type RegisterStep3Errors = {
  goals: string;
  agree_participation_visibility: string;
  cpv_ids: string;
  form: string;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const clearErrorBag = <T extends Record<string, string>>(errors: T) => {
  for (const key of Object.keys(errors) as Array<keyof T>) {
    errors[key] = "";
  }
};

const validateEmail = (email: string): boolean => {
  return EMAIL_REGEX.test(email.trim());
};

const getExpectedCodeLength = (subjectType: SubjectType) => {
  if (subjectType === "legal_resident") return 8;
  if (subjectType === "fop_resident" || subjectType === "individual") return 10;
  return null;
};

export const useAuthFormsValidation = () => {
  const showErrors = ref(false);
  const visibleError = (error: string) => (showErrors.value ? error : "");
  const enableErrors = () => {
    showErrors.value = true;
  };
  const disableErrors = () => {
    showErrors.value = false;
  };

  const requiredRingClass = (error: string, required = true) => {
    if (!required) return "!ring-black";
    if (!showErrors.value) return "!ring-black";
    return error ? "!ring-error" : "!ring-black";
  };

  const requiredBorderClass = (error: string, required = true) => {
    if (!required) return "!border-black";
    if (!showErrors.value) return "!border-black";
    return error ? "!border-error" : "!border-black";
  };

  const createLoginErrors = (): LoginFormErrors => ({
    email: "",
    password: "",
    form: "",
  });

  const createRegisterStep1Errors = (): RegisterStep1Errors => ({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    password: "",
    form: "",
  });

  const createRegisterStep2Errors = (): RegisterStep2Errors => ({
    subject_type: "",
    edrpou: "",
    name: "",
    registration_country: "",
    company_address: "",
    identity_document: "",
    agree_trade_rules: "",
    agree_privacy_policy: "",
    form: "",
  });

  const createRegisterStep3Errors = (): RegisterStep3Errors => ({
    goals: "",
    agree_participation_visibility: "",
    cpv_ids: "",
    form: "",
  });

  const resetLoginErrors = (errors: LoginFormErrors) => clearErrorBag(errors);
  const resetRegisterStep1Errors = (errors: RegisterStep1Errors) =>
    clearErrorBag(errors);
  const resetRegisterStep2Errors = (errors: RegisterStep2Errors) =>
    clearErrorBag(errors);
  const resetRegisterStep3Errors = (errors: RegisterStep3Errors) =>
    clearErrorBag(errors);

  const validateLoginForm = (form: LoginFormState, errors: LoginFormErrors) => {
    resetLoginErrors(errors);
    let valid = true;

    const email = String(form.email ?? "").trim();
    if (!email) {
      errors.email = "Вкажіть email.";
      valid = false;
    } else if (!validateEmail(email)) {
      errors.email = "Вкажіть коректний email.";
      valid = false;
    }

    if (!String(form.password ?? "").trim()) {
      errors.password = "Вкажіть пароль.";
      valid = false;
    }

    return valid;
  };

  const validateRegisterStep1Form = (
    form: RegisterStep1FormState,
    errors: RegisterStep1Errors,
  ) => {
    resetRegisterStep1Errors(errors);
    let valid = true;

    if (!String(form.last_name || "").trim()) {
      errors.last_name = "Заповніть прізвище.";
      valid = false;
    }
    if (!String(form.first_name || "").trim()) {
      errors.first_name = "Заповніть ім'я.";
      valid = false;
    }

    const phone = String(form.phone || "").trim();
    if (!phone) {
      errors.phone = "Введіть номер телефону.";
      valid = false;
    } else if (phone.length !== 9) {
      errors.phone = "Введіть повний номер телефону (9 цифр після +380).";
      valid = false;
    }

    const email = String(form.email || "").trim();
    if (!email) {
      errors.email = "Вкажіть email.";
      valid = false;
    } else if (!validateEmail(email)) {
      errors.email = "Вкажіть коректний email.";
      valid = false;
    }

    if (!String(form.password || "").trim()) {
      errors.password = "Вкажіть пароль.";
      valid = false;
    }

    return valid;
  };

  const validateRegisterStep2Form = (
    form: RegisterStep2FormState,
    errors: RegisterStep2Errors,
    options: { shouldUseExistingCompanyFlow: boolean },
  ) => {
    resetRegisterStep2Errors(errors);
    let valid = true;

    if (!String(form.subject_type || "").trim()) {
      errors.subject_type = "Оберіть тип суб'єкта.";
      valid = false;
    }

    const code = String(form.edrpou ?? "").trim();
    if (!code) {
      errors.edrpou = "Заповніть код.";
      valid = false;
    }

    const expectedLen = getExpectedCodeLength(form.subject_type);
    if (code && expectedLen && code.length !== expectedLen) {
      if (form.subject_type === "legal_resident") {
        errors.edrpou = "Код ЄДРПОУ має містити 8 цифр.";
      } else if (form.subject_type === "fop_resident") {
        errors.edrpou = "ІПН має містити 10 цифр.";
      } else {
        errors.edrpou = "Ідентифікаційний код має містити 10 цифр.";
      }
      valid = false;
    }

    if (!options.shouldUseExistingCompanyFlow) {
      if (form.subject_type !== "individual" && !form.name.trim()) {
        errors.name = "Заповніть назву згідно уставних документів.";
        valid = false;
      }

      if (form.subject_type === "non_resident" && !form.registration_country) {
        errors.registration_country = "Оберіть країну реєстрації.";
        valid = false;
      }

      if (!form.company_address.trim()) {
        errors.company_address = "Заповніть адресу.";
        valid = false;
      }

      if (form.subject_type === "individual" && !form.identity_document) {
        errors.identity_document = "Завантажте документ, що підтверджує особу.";
        valid = false;
      }
    }

    if (!form.agree_trade_rules) {
      errors.agree_trade_rules = "Потрібно погодитися з регламентом торгів.";
      valid = false;
    }
    if (!form.agree_privacy_policy) {
      errors.agree_privacy_policy =
        "Потрібно погодитися з політикою конфіденційності.";
      valid = false;
    }

    return valid;
  };

  const validateRegisterStep3Form = (
    form: RegisterStep3FormState,
    cpvIds: number[],
    errors: RegisterStep3Errors,
  ) => {
    resetRegisterStep3Errors(errors);

    if (!form.goal_tenders && !form.goal_participation) {
      errors.goals = "Оберіть хоча б один напрямок діяльності.";
      return false;
    }

    if (form.goal_participation) {
      if (!form.agree_participation_visibility) {
        errors.agree_participation_visibility =
          "Підтвердьте відображення реєстраційних даних.";
        return false;
      }
      if (!cpvIds.length) {
        errors.cpv_ids = "Оберіть хоча б одну CPV-категорію.";
        return false;
      }
    }

    return true;
  };

  return {
    expectedCodeLength: getExpectedCodeLength,
    requiredRingClass,
    requiredBorderClass,
    createLoginErrors,
    createRegisterStep1Errors,
    createRegisterStep2Errors,
    createRegisterStep3Errors,
    resetLoginErrors,
    resetRegisterStep1Errors,
    resetRegisterStep2Errors,
    resetRegisterStep3Errors,
    validateLoginForm,
    validateRegisterStep1Form,
    validateRegisterStep2Form,
    validateRegisterStep3Form,
    showErrors,
    enableErrors,
    disableErrors,
    visibleError,
  };
};
