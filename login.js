schoolApp.controller("LoginController", ['$scope', '$http', '$q', '$timeout', '$window', function ($scope, $http, $q, $timeout, $window) {

    $scope.DoLoginUrl = "/security/dologin";
    $scope.CheckUserAndRoleUrl = "/security/checkUserAndRole";
    $scope.resendOtpUrl = "/security/resendOtp";
    $scope.ResetOrForgotPasswordUrl = "/ResetOrForgotPassword";
    $scope.VerifyReCaptchaTokenUrl = "/security/VerifyReCaptchaToken";
    $scope.GenerateCaptchaUrl = "/GenerateCaptcha";
    $scope.VerifyOtpUrl = "/security/verifyotp";

    $scope.CheckUserAndRoleNewUrl = "/security/checkUserAndRoleNew";


    $scope.Login = angular.fromJson($("#HiddenField").val());
    $scope.LoginType = "F";
    $scope.UsernameKey = "";
    InitializeNgMethods($scope, $http);
    $(".preloader").fadeOut();
    $scope.MainLogin = true;
    $scope.ForgotPasswordView = false;
    $scope.SelectRole = false;
    $scope.TermCondition = false;
    $scope.RefudPolicy = false;
    $scope.ContactUs = false;
    $scope.PrivacyPolicy = false;
    $scope.SupportingSoft = false;
    $scope.OtpVerificationScreen = false;
    $scope.SendSMSEmail = false;
    $scope.SelectRoleScreen = false;
    $scope.EmptyUserNameAndPassword = false;
    $scope.MaxPassword = false;
    $scope.MaxUsername = false;
    $scope.InvalidOtpMessage = false;
    //$scope.LoginScreen = false;
    $scope.SMSMessageSent = false;
    var countdownInterval; // keep reference globally
    $scope.loginDisabled = false;
    $scope.SuccessMessage = null;
    function startOtpCountdown() {

        const timerElement = document.getElementById('timer');
        if (timerElement) {
            let timeLeft = 60;
            $scope.resendEnabled = false;
            $scope.OTPExpired = false;

            timerElement.textContent = timeLeft; // reset to 60

            // clear any existing interval before starting new one
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }

            countdownInterval = setInterval(function () {
                timeLeft--;

                if (timeLeft <= 0) {
                    clearInterval(countdownInterval);
                    $scope.$apply(function () {
                        timerElement.textContent = "0";
                        $scope.resendEnabled = true;  // enable button again
                        $scope.OTPExpired = true;     // optional flag
                    });
                } else {
                    $scope.$apply(function () {
                        timerElement.textContent = timeLeft;
                    });
                }
            }, 1000);
        }
    }


    $scope.OpenClosePanel = function (name) {
        $scope.MainLogin = false;
        $scope.ForgotPasswordView = false;
        $scope.SelectRole = false;
        $scope.TermCondition = false;
        $scope.RefudPolicy = false;
        $scope.ContactUs = false;
        $scope.PrivacyPolicy = false;
        $scope.SupportingSoft = false;
        if (name === 'T') {
            $scope.TermCondition = true;
        }
        else if (name === 'S') {
            $scope.SupportingSoft = true;
        }
        else if (name === 'R') {
            $scope.RefudPolicy = true;
        }
        else if (name === 'C') {
            $scope.ContactUs = true;
        }
        else if (name === 'P') {
            $scope.PrivacyPolicy = true;
        }
        else {
            $scope.MainLogin = true;
        }
        $timeout(function () {
            $("#panel").scrollTop(0);
        });
    };


    //$(document).ready(function () {
    //    
    //        $scope.MakeHttpCall(Constants.Post, $scope.GenerateCaptchaUrl, null, Constants.ApplicationJson).then(function (response) {
    //            if (response.IsSuccess) {
    //                
    //                $('#captcha-container').html(response.Data);
    //            }
    //        });

    //});

    $(document).ready(function () {

        $.post('/Generate', function (response) {
            $('#captcha-container').html('<img src="data:image/gif;base64,' + response.ImageBase64 + '" alt="Captcha" />');
        });
    });

    $scope.CheckUserAndRoleNewLogin = function () {
        if ($scope.loginDisabled) return;
        try {
            $(".preloader").fadeIn();
            $scope.loginDisabled = true;
            var DeviceName = "";
            angular.element("#EmptyUserNameAndPassword").css("display", "none");
            angular.element("#InValidUserNameAndPassword").css("display", "none");
            angular.element("#MaxPassword").css("display", "none");
            angular.element("#MaxUsername").css("display", "none");
            angular.element("#NoRole").css("display", "none");
            angular.element("#InValidCaptcha").css("display", "none");
            angular.element("#UnverifyCaptcha").css("display", "none");
            angular.element("#NoMoEmail").css("display", "none");

            var userAgent = navigator.userAgent;
            if (userAgent.match(/Android/i) || userAgent.match(/webOS/i) || userAgent.match(/iPhone/i) || userAgent.match(/iPad/i) || userAgent.match(/iPod/i) || userAgent.match(/BlackBerry/i) || userAgent.match(/Windows Phone/i)) {
                DeviceName = "Mobile";
            } else {
                DeviceName = "Web";
            }
            var browserNameRegex = /(Chrome|Firefox|Edge|Safari)/i;
            var versionRegex = /(Chrome|Firefox|Edge|Safari)\/([\d.]+)/i;

            // Match browser name
            var browserNameMatch = userAgent.match(browserNameRegex);
            var browserName = browserNameMatch ? browserNameMatch[1] : "Unknown";

            // Match browser version
            var versionMatch = userAgent.match(versionRegex);
            var browserVersion = versionMatch ? versionMatch[2] : "Unknown";

            if ($scope.UsernameKey === "" || $scope.UsernameKey === undefined) {
                $scope.loginDisabled = false;
                angular.element("#EmptyUserNameAndPassword").css("display", "block");
            }
            else if ($scope.UsernameKey.length > 10) {
                $scope.loginDisabled = false;
                //    $scope.MaxUsername = true;
                angular.element("#MaxUsername").css("display", "block");

            }
            else if ($scope.Login == null && $scope.Login == undefined || $scope.Login.Password == null) {
                $scope.loginDisabled = false;
                //    $scope.EmptyUserNameAndPassword = true;
                angular.element("#EmptyUserNameAndPassword").css("display", "block");

            }
            else if ($scope.Login?.Password?.length > 20) {
                $scope.loginDisabled = false;
                //    $scope.MaxPassword = true;
                angular.element("#MaxPassword").css("display", "block");
            }
            else if (!$scope.Login.RecaptchaResponse) {
                $scope.loginDisabled = false;
                //$scope.InValidCaptcha = true;
                angular.element("#InValidCaptcha").css("display", "block");
                angular.element("#UnverifyCaptcha").css("display", "none");
            } else {
                if ($scope.Login.RecaptchaResponse) {
                    $scope.Login.Username = $scope.LoginType + "" + $scope.UsernameKey;
                    $scope.Login.DeviceName = DeviceName;
                    $scope.Login.BrowserName = browserName;
                    $scope.Login.BrowserVersion = browserVersion;
                    let jsonDatanew = angular.toJson({ loginModel: $scope.Login });
                    $scope.MakeHttpCall(Constants.Post, $scope.CheckUserAndRoleUrl, jsonDatanew, Constants.ApplicationJson ).then(function (response) {
                        if (response.IsSuccess) {
                            $scope.UserMobile = response.Data2.UserMobile || null;
                            $scope.UserEmailId = response.Data2.UserEmailId || null;
                            $scope.EnableTwoFactor = response.Data2.EnableTwoFactor || null;

                            $scope.MaskemailId = response.Data2.MaskemailId || null;
                            $scope.Maskmobile = response.Data2.Maskmobile || null;

                            $scope.Login.IsSentViaSMS = false;
                            $scope.Login.IsSentViaMAIL = false;


                            if ($scope.EnableTwoFactor && !$scope.UserMobile && !$scope.UserEmailId) {
                                angular.element("#NoMoEmail").css("display", "block");

                                $scope.loginDisabled = false;
                                $(".preloader").fadeOut();
                                return;
                            }
                            if ($scope.UserEmailId && $scope.UserMobile) {
                                $scope.Login.IsSentViaMAIL = true;
                            }
                            else if ($scope.UserEmailId) {
                                $scope.Login.IsSentViaMAIL = true;
                            }
                            else if ($scope.UserMobile) {
                                $scope.Login.IsSentViaSMS = true;
                            }


                            if (response.Data2.IsTwoFA === true && response.Data.RoleList.length > 0) {
                                $scope.loginDisabled = false;
                                // Just show the OTP section
                                $scope.OtpVerificationScreen = false;
                                $scope.SendSMSEmail = true;
                                $scope.SelectRoleScreen = false;
                                $scope.SchoolName = response.Data2.schoolName;
                                $scope.loginModel = response.Data;
                                $scope.userDetails = response.Data2;
                                $scope.MaskingPhoneNumber = response.Data2.MaskingPhoneNumber;
                                $scope.MaskingEMailID = response.Data2.MaskingEMailID;
                                $timeout(startOtpCountdown, 200);
                                $scope.RoleList = response.Data.RoleList;
                                if ($scope.RoleList.length === 1) {
                                    $scope.Login.RoleId = $scope.RoleList[0].RoleId;
                                }
                                if ($scope.RoleList.length > 1) {
                                    $scope.RoleList.forEach(function (role) {
                                        if (role.IsDefault === true) {
                                            $scope.Login.RoleId = role.RoleId;
                                            return false;
                                        }
                                    });
                                }
                            }
                           
                            else if (response.Data2.IsTwoFA === false) {
                                $scope.MainLogin = false;
                                $scope.SelectRole = true;
                                $scope.RoleList = response.Data.RoleList;
                                if ($scope.RoleList.length === 0) {
                                    //    $scope.NoRole = true;
                                    angular.element("#NoRole").css("display", "block");

                                }
                                else {
                                    $scope.SelectRoleScreen = true;
                                    $scope.OtpVerificationScreen = false;
                                    $scope.SchoolName = response.Data2.schoolName;
                                }
                                if ($scope.RoleList.length === 1) {
                                    $scope.Login.RoleId = $scope.RoleList[0].RoleId;
                                    /* $scope.DoLogin();*/
                                    $timeout(function () {
                                        $scope.DoLogin();
                                    }, 100); 
                                }
                                if ($scope.RoleList.length > 1) {
                                    $scope.RoleList.forEach(function (role) {
                                        if (role.IsDefault === true) {
                                            $scope.Login.RoleId = role.RoleId;
                                            return false;
                                        }
                                    });
                                }
                            }
                        } else {
                            if (response.CustomReturn === 'TempBlockAccess') {
                                $window.location = "/TempBlockAccessScreen";
                            }
                            if (response.Message == "Captcha verification failed..!") {
                                //    $scope.UnverifyCaptcha = true;
                                angular.element("#UnverifyCaptcha").css("display", "block");

                            }
                            if (response.Message == "UserName Or Password Not Matched..!") {
                                //    $scope.InValidUserNameAndPassword = true;
                                angular.element("#InValidUserNameAndPassword").css("display", "block");
                            }

                            $scope.Login.RecaptchaResponse = null;
                            $.post('/Generate', function (response) {
                                $('#captcha-container').html('<img src="data:image/gif;base64,' + response.ImageBase64 + '" alt="Captcha" />');
                            });
                            $scope.loginDisabled = false;
                        }
                    });
                }
            }
            $(".preloader").fadeOut();
        } catch (e) {
            $(".preloader").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };

    $scope.RefreshCaptchNew = function () {

        $.post('/Generate', function (response) {
            $('#captcha-container').html('<img src="data:image/gif;base64,' + response.ImageBase64 + '" alt="Captcha" />');
        });
    }


    $scope.DoLogin = function () {
        try {

            $(".preloaderCenter").fadeIn();
            $scope.Login.Username = $scope.LoginType + "" + $scope.UsernameKey;
            let jsonData = angular.toJson({ loginModel: $scope.Login });
            $scope.MakeHttpCall(Constants.Post, $scope.DoLoginUrl, jsonData, Constants.ApplicationJson).then(function (response) {

                if (response.IsSuccess) {

                    //if (response.Data !== null) {
                    //    $window.localStorage.SessionExists = true;
                    //    //    $window.localStorage.UserName = response.Data.userName;
                    //    //    $window.localStorage.Auth = response.Data.auth;
                    //    //    $window.localStorage.DataSource = response.Data.dataSource;
                    //    //    $window.localStorage.DbUserId = response.Data.dbUserId;
                    //    //    $window.localStorage.InitialCatalog = response.Data.initialCatalog;
                    //    //    $window.localStorage.Password = response.Data.password;
                    //    //    $window.localStorage.SchoolId = response.Data.schoolId;
                    //    //    $window.localStorage.UserMenu = JSON.stringify(response.Data.UserFeatureMenuPermission);
                    //}
                    //ShowNotification(Notification.success, response.Message,'top right');

                    //$scope.MainLogin = false;
                    //$scope.SelectRole = true;

                    $window.location = "/";
                }
                else {
                    if (response.CustomReturn === 'TempBlockAccess') {
                        $window.location = "/TempBlockAccessScreen";
                    }

                    ShowNotification(Notification.error, response.Message, 'top right');
                }
                $(".preloaderCenter").fadeOut();
            });
        } catch (e) {
            $(".preloader").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };

    $scope.initOtp = function () {

        $timeout(function () {
            initOtpInputs("otp-container"); // call global function
        }, 0); // run after digest cycle
    };

    //function initOtpInputs(containerId) {

    //    const otpInputs = document.querySelectorAll(`#${containerId} input`);

    //    otpInputs.forEach((input, index) => {
    //        input.addEventListener('keyup', (e) => {
    //            if (e.key === 'Tab') return; // let tab work

    //            if (/^[0-9]$/.test(e.key)) {
    //                input.value = e.key; // replace with digit
    //                if (index < otpInputs.length - 1) {
    //                    otpInputs[index + 1].focus();
    //                } else {
    //                    // Last input ? focus the Verify OTP button
    //                    document.getElementById("Submit_btn").focus();
    //                }
    //            } else if (e.key === 'Backspace') {
    //                input.value = '';
    //                if (index > 0) {
    //                    otpInputs[index - 1].focus();
    //                }
    //            } else {
    //                input.value = ''; // block invalid chars
    //            }

    //        });

    //        // auto select when focusing
    //        input.addEventListener('focus', () => input.select());
    //    });
    //}
    function initOtpInputs(containerId) {
        const otpInputs = document.querySelectorAll(`#${containerId} input`);

        otpInputs.forEach((input, index) => {
            // handle numeric input (works on Chrome & mobile)
            input.addEventListener('input', (e) => {
                const value = e.target.value.replace(/\D/g, ''); // allow only digits
                input.value = value;

                if (value && index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                } else if (value && index === otpInputs.length - 1) {
                    const submitBtn = document.getElementById('Submit_btn');
                    if (submitBtn) submitBtn.focus();
                }
            });

            // handle backspace navigation
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !input.value && index > 0) {
                    otpInputs[index - 1].focus();
                }
            });

            // auto-select on focus
            input.addEventListener('focus', () => input.select());
        });

        // optional: allow pasting full OTP
        otpInputs[0].addEventListener('paste', (e) => {
            e.preventDefault();
            const pasted = e.clipboardData.getData('text').replace(/\D/g, '');
            otpInputs.forEach((inp, i) => inp.value = pasted[i] || '');
            if (pasted.length === otpInputs.length) {
                const submitBtn = document.getElementById('Submit_btn');
                if (submitBtn) submitBtn.focus();
            }
        });
    }

    $scope.ResendOtp = function () {
        debugger;
        try {
            if (!$scope.resendEnabled) return;
            let isMailSelected = $scope.Login.IsSentViaMAIL;
            let isSmsSelected = $scope.Login.IsSentViaSMS;

          
            if (isMailSelected && !isSmsSelected) {
                $scope.Login.IsSentViaSMS = false;
            }

            if (isSmsSelected && !isMailSelected) {
                $scope.Login.IsSentViaMAIL = false;
            }
          
            $scope.InvalidOtp = false;
            document.getElementById("otp-1").value = "";
            document.getElementById("otp-2").value = "";
            document.getElementById("otp-3").value = "";
            document.getElementById("otp-4").value = "";
            $(".preloaderCenter").fadeIn();
            $scope.Login.Username = $scope.LoginType + "" + $scope.UsernameKey;
            let jsonData = angular.toJson({ userDetails: $scope.userDetails, loginModel: $scope.loginModel });
            $scope.MakeHttpCall(Constants.Post, $scope.resendOtpUrl, jsonData, Constants.ApplicationJson).then(function (response) {
                if (response.IsSuccess) {
                    startOtpCountdown();
                    $scope.loginModel = response.Data;
                    $scope.userDetails = response.Data2;
                    $scope.MaskingPhoneNumber = response.Data2.MaskingPhoneNumber;
                    $scope.Maskmobile = response.Data2.Maskmobile;
                  
                }
                else {
                    $scope.MaskingPhoneNumber = null;
                    $scope.MaskingEMailID = null;
                    if (response.CustomReturn === 'TempBlockAccess') {
                        $window.location = "/TempBlockAccessScreen";
                    }
                }
                $(".preloaderCenter").fadeOut();
            });
        } catch (e) {
            $(".preloaderCenter").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };

    $scope.ForgotPasswordMethod = function () {
        $scope.MainLogin = false;
        $scope.ForgotPasswordView = true;
    };
    $scope.BackToLoginMethod = function () {

        $scope.ResetValidation("#ForgotPasswordForm");
        $scope.MainLogin = true;
        $scope.ForgotPasswordView = false;
        $scope.SelectRole = false;
        $scope.Login.UserId = null;
        $scope.Login.MobileNo = null;
    };

    $scope.SendSMSMethod = function () {

        try {
            angular.element("#InValidUserNameAndMobile").css("display", "none");

            /*if ($("#ForgotPasswordForm").valid()) {*/
            $(".preloaderCenter").fadeIn();
            if ($scope.SMSMessageSent) return;
            $scope.SMSMessageSent = true;
            $scope.SuccessMessage = null;
            if ($scope.UsernameKey == null || $scope.UsernameKey == "" || $scope.UsernameKey == "Undefined" || $scope.MobileNo == null) {
                //$scope.InvalidOtp = true;
                angular.element("#InValidUserNameAndMobile").css("display", "block");
                $(".preloaderCenter").fadeOut();
                return;
            }
            $scope.Login = $scope.Login || {};
            $scope.Login.Username = $scope.LoginType + "" + $scope.UsernameKey;
            $scope.Login.MobileNo = $scope.MobileNo;
            $scope.Login.UserId = $scope.UsernameKey;
            let jsonData = angular.toJson({ loginModel: $scope.Login });
            $scope.MakeHttpCall(Constants.Post, $scope.ResetOrForgotPasswordUrl, jsonData, Constants.ApplicationJson).then(function (response) {
                if (response.IsSuccess) {
                    $scope.Login.UserId = null;
                    $scope.Login.MobileNo = null;
                    $scope.SuccessMessage = 'Email has been sent to your registered mail Id.';

                    setTimeout(function () {
                        window.location.href = "/Login";
                        $scope.SMSMessageSent = false;
                    }, 6000);
                }
                else {
                    if (response.Message === "notExists") {
                        angular.element("#InValidUserNameAndMobile").css("display", "block");
                    }
                    else if (response.Message === "EmailNotFound") {
                        angular.element("#EmailIsNotExist").css("display", "block");
                    }
                    else {
                        ShowNotification(Notification.error, response.Message, 'top right');
                    }
                }
                $(".preloaderCenter").fadeOut();
            });
            $(".preloaderCenter").fadeOut();

            /*}*/
        } catch (e) {
            $(".preloaderCenter").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };

    $scope.BackToLoginNew = function () {
        window.location.href = "/Login";
    };
    $scope.BackToLogin = function () {
        window.location.href = "/Login";
    }
    $scope.VerifyOtp = function () {
        try {
            $(".preloaderCenter").fadeIn();
            angular.element("#InvalidOtp").css("display", "none");
            var otpValue1 = document.getElementById("otp-1").value;
            var otpValue2 = document.getElementById("otp-2").value;
            var otpValue3 = document.getElementById("otp-3").value;
            var otpValue4 = document.getElementById("otp-4").value;

            if (otpValue1 && otpValue2 && otpValue3 && otpValue4 == null) {
                //$scope.InvalidOtp = true;
                angular.element("#InvalidOtp").css("display", "block");
                return;
            }

            var fullOtp = otpValue1 + otpValue2 + otpValue3 + otpValue4;

            let jsonData = angular.toJson({
                OtpRequestId: $scope.userDetails.OtpRequestId,
                userId: $scope.userDetails.userId,
                otp: fullOtp
            });

            $scope.MakeHttpCall(Constants.Post, $scope.VerifyOtpUrl, jsonData, Constants.ApplicationJson)
                .then(function (response) {

                    if (response.CustomReturn === "true") {
                       
                        $scope.SelectRoleScreen = true;                        
                        $scope.OtpVerificationScreen = false;

                        if ($scope.RoleList.length === 1) {
                            $scope.Login.RoleId = $scope.RoleList[0].RoleId;
                            /* $scope.DoLogin();*/
                            $timeout(function () {
                                $scope.DoLogin();
                            }, 100);
                        }
                        if ($scope.RoleList.length > 1) {
                            $scope.RoleList.forEach(function (role) {
                                if (role.IsDefault === true) {
                                    $scope.Login.RoleId = role.RoleId;
                                    return false;
                                }
                            });
                        }

                        // Use $timeout so Angular finishes rendering before applying focus
                        $timeout(function () {
                            var btn = document.getElementById("roleSubmit_btn");
                            if (btn) {
                                btn.focus();
                            }
                        }, 0);

                    } else {
                        angular.element("#InvalidOtp").css("display", "block");
                        $scope.InvalidOtpMessage = response.Message;
                    }

                });
            $(".preloaderCenter").fadeOut();
        } catch (e) {
            $(".preloaderCenter").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };
    $scope.CheckUserAndRoleNewLoginScreen = function () {
        if ($scope.loginDisabled) return;
        try {
            $(".preloader").fadeIn();
            $scope.loginDisabled = true;
            var DeviceName = "";
            angular.element("#EmptyUserNameAndPassword").css("display", "none");
            angular.element("#InValidUserNameAndPassword").css("display", "none");
            angular.element("#MaxPassword").css("display", "none");
            angular.element("#MaxUsername").css("display", "none");
            angular.element("#NoRole").css("display", "none");
            angular.element("#InValidCaptcha").css("display", "none");
            angular.element("#UnverifyCaptcha").css("display", "none");

            var userAgent = navigator.userAgent;
            if (userAgent.match(/Android/i) || userAgent.match(/webOS/i) || userAgent.match(/iPhone/i) || userAgent.match(/iPad/i) || userAgent.match(/iPod/i) || userAgent.match(/BlackBerry/i) || userAgent.match(/Windows Phone/i)) {
                DeviceName = "Mobile";
            } else {
                DeviceName = "Web";
            }
            var browserNameRegex = /(Chrome|Firefox|Edge|Safari)/i;
            var versionRegex = /(Chrome|Firefox|Edge|Safari)\/([\d.]+)/i;

            // Match browser name
            var browserNameMatch = userAgent.match(browserNameRegex);
            var browserName = browserNameMatch ? browserNameMatch[1] : "Unknown";

            // Match browser version
            var versionMatch = userAgent.match(versionRegex);
            var browserVersion = versionMatch ? versionMatch[2] : "Unknown";

            if ($scope.UsernameKey === "" || $scope.UsernameKey === undefined) {
                $scope.loginDisabled = false;
                angular.element("#EmptyUserNameAndPassword").css("display", "block");
            }
            else if ($scope.UsernameKey.length > 10) {
                $scope.loginDisabled = false;
                //    $scope.MaxUsername = true;
                angular.element("#MaxUsername").css("display", "block");

            }
            else if ($scope.Login == null && $scope.Login == undefined || $scope.Login.Password == null) {
                $scope.loginDisabled = false;
                //    $scope.EmptyUserNameAndPassword = true;
                angular.element("#EmptyUserNameAndPassword").css("display", "block");

            }
            else if ($scope.Login?.Password?.length > 20) {
                $scope.loginDisabled = false;
                //    $scope.MaxPassword = true;
                angular.element("#MaxPassword").css("display", "block");
            }
            else if ($scope.Login?.Password?.length > 20) {
                $scope.loginDisabled = false;
                angular.element("#MaxPassword").css("display", "block");
            }
            angular.element("#OptionError").css("display", "none");

            // Validation
            if (!$scope.Login.IsSentViaMAIL && !$scope.Login.IsSentViaSMS) {
                angular.element("#OptionError").css("display", "block");
                $scope.loginDisabled = false;
                $(".preloader").fadeOut();
                return;
            }

            else if (!$scope.Login.RecaptchaResponse) {
                $scope.loginDisabled = false;
                //$scope.InValidCaptcha = true;
                angular.element("#InValidCaptcha").css("display", "block");
                angular.element("#UnverifyCaptcha").css("display", "none");
            } else {
                if ($scope.Login.RecaptchaResponse) {
                    $scope.Login.Username = $scope.LoginType + "" + $scope.UsernameKey;
                    $scope.Login.DeviceName = DeviceName;
                    $scope.Login.BrowserName = browserName;
                    $scope.Login.BrowserVersion = browserVersion;
                    let jsonDatanew = angular.toJson({ loginModel: $scope.Login });
                    $scope.MakeHttpCall(Constants.Post, $scope.CheckUserAndRoleNewUrl, jsonDatanew, Constants.ApplicationJson).then(function (response) {
                        if (response.IsSuccess) {

                            if (response.Data2.IsTwoFA === true && response.Data.RoleList.length > 0) {
                                $scope.loginDisabled = false;
                                $scope.SendSMSEmail = false;
                                // Just show the OTP section
                                $scope.OtpVerificationScreen = true;
                                $scope.SelectRoleScreen = false;
                                $scope.SchoolName = response.Data2.schoolName;
                                $scope.loginModel = response.Data;
                                $scope.userDetails = response.Data2;
                                $scope.MaskingPhoneNumber = response.Data2.Maskmobile;
                                $scope.MaskingEMailID = response.Data2.MaskemailId;
                                $timeout(startOtpCountdown, 200);
                                $scope.RoleList = response.Data.RoleList;
                                if ($scope.RoleList.length === 1) {
                                    $scope.Login.RoleId = $scope.RoleList[0].RoleId;
                                }
                                if ($scope.RoleList.length > 1) {
                                    $scope.RoleList.forEach(function (role) {
                                        if (role.IsDefault === true) {
                                            $scope.Login.RoleId = role.RoleId;
                                            return false;
                                        }
                                    });
                                }
                            }
                            else if (response.Data2.IsTwoFA === false) {
                                $scope.MainLogin = false;
                                $scope.SelectRole = true;
                                $scope.RoleList = response.Data.RoleList;
                                if ($scope.RoleList.length === 0) {
                                    //    $scope.NoRole = true;
                                    angular.element("#NoRole").css("display", "block");

                                }
                                else {
                                    $scope.SelectRoleScreen = true;
                                    $scope.OtpVerificationScreen = false;
                                    $scope.SchoolName = response.Data2.schoolName;
                                }
                                if ($scope.RoleList.length === 1) {
                                    $scope.Login.RoleId = $scope.RoleList[0].RoleId;
                                }
                                if ($scope.RoleList.length > 1) {
                                    $scope.RoleList.forEach(function (role) {
                                        if (role.IsDefault === true) {
                                            $scope.Login.RoleId = role.RoleId;
                                            return false;
                                        }
                                    });
                                }
                            }
                        } else {
                            if (response.CustomReturn === 'TempBlockAccess') {
                                $window.location = "/TempBlockAccessScreen";
                            }
                            if (response.Message == "Captcha verification failed..!") {
                                //    $scope.UnverifyCaptcha = true;
                                angular.element("#UnverifyCaptcha").css("display", "block");

                            }
                            if (response.Message == "UserName Or Password Not Matched..!") {
                                //    $scope.InValidUserNameAndPassword = true;
                                angular.element("#InValidUserNameAndPassword").css("display", "block");
                            }

                            $scope.Login.RecaptchaResponse = null;
                            $.post('/Generate', function (response) {
                                $('#captcha-container').html('<img src="data:image/gif;base64,' + response.ImageBase64 + '" alt="Captcha" />');
                            });
                            $scope.loginDisabled = false;
                        }
                    });
                }
            }
            $(".preloader").fadeOut();
        } catch (e) {
            $(".preloader").fadeOut();
            ShowNotification(Notification.error, window.RequestFailed);
        }
    };


}]);